import logging
from unittest.mock import AsyncMock, MagicMock, call, patch

from limits.aio import strategies
from limits.aio.storage import RedisStorage
import pytest
from redis.exceptions import RedisError

from api.helpers._limiter import Limiter
from api.schemas.admin.roles import Limit, LimitType
from api.schemas.core.configuration import LimitingStrategy
from api.schemas.me.info import UserInfo
from api.utils.exceptions import InsufficientPermissionException, ModelNotFoundException, RateLimitExceeded

logger = logging.getLogger(__name__)

# =========================== STRATEGIES ============================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "strategy, expected_class",
    [
        (LimitingStrategy.MOVING_WINDOW, strategies.MovingWindowRateLimiter),
        (LimitingStrategy.FIXED_WINDOW, strategies.FixedWindowRateLimiter),
        (LimitingStrategy.SLIDING_WINDOW, strategies.SlidingWindowCounterRateLimiter),
    ],
)
async def test_limiter_initialization_strategies(strategy, expected_class):
    """Test that Limiter initializes the correct strategy class."""
    mock_redis_pool = MagicMock()
    mock_redis_pool.url = "redis://localhost:6379"

    with patch("api.helpers._limiter.storage.RedisStorage") as MockStorage, patch("api.helpers._limiter.Redis"):
        MockStorage.return_value = AsyncMock(spec=RedisStorage)

        limiter = Limiter(mock_redis_pool, strategy=strategy)
        assert isinstance(limiter.strategy, expected_class)


# =========================== RESET METHOD ============================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "strategy",
    [
        LimitingStrategy.MOVING_WINDOW,
        LimitingStrategy.FIXED_WINDOW,
        LimitingStrategy.SLIDING_WINDOW,
    ],
)
async def test_limiter_reset_success(strategy):
    """Test that reset successfully calls redis_client.reset()."""
    # Mock the Redis pool instead of using global_context
    mock_redis_pool = MagicMock()
    mock_redis_pool.url = "redis://localhost:6379"

    with patch("api.helpers._limiter.storage.RedisStorage") as MockStorage, patch("api.helpers._limiter.Redis") as MockRedis:
        mock_storage_instance = AsyncMock(spec=RedisStorage)
        MockStorage.return_value = mock_storage_instance

        mock_internal_redis = AsyncMock()
        MockRedis.return_value = mock_internal_redis

        redis_state = ["LIMITS:key1", "LIMITS:key2"]
        mock_internal_redis.keys.side_effect = lambda pattern: redis_state
        # When storage.reset() is called, clear the state

        async def simulate_reset():
            redis_state.clear()

        mock_storage_instance.reset.side_effect = simulate_reset

        limiter = Limiter(mock_redis_pool, strategy=strategy)

        # Verify keys exist before reset
        initial_keys = await limiter.redis_client.keys("LIMITS*")
        assert len(initial_keys) == 2

        await limiter.reset()

        mock_storage_instance.reset.assert_awaited_once()

        final_keys = await limiter.redis_client.keys("LIMITS*")
        assert len(final_keys) == 0


@pytest.mark.asyncio
async def test_limiter_reset_handles_redis_error():
    """Test that reset handles RedisError gracefully."""
    mock_redis_pool = MagicMock()
    mock_redis_pool.url = "redis://localhost:6379"
    strategy = LimitingStrategy.FIXED_WINDOW

    with (
        patch("api.helpers._limiter.storage.RedisStorage") as MockStorage,
        patch("api.helpers._limiter.Redis") as MockRedis,
        patch("api.helpers._limiter.logger") as mock_logger,
    ):
        mock_storage_instance = AsyncMock(spec=RedisStorage)
        mock_storage_instance.reset.side_effect = RedisError("Test Error")
        MockStorage.return_value = mock_storage_instance

        mock_internal_redis = AsyncMock()
        MockRedis.return_value = mock_internal_redis

        limiter = Limiter(mock_redis_pool, strategy)

        await limiter.reset()

        mock_storage_instance.reset.assert_awaited_once()
        mock_logger.error.assert_called_once()
        logged_msg = mock_logger.error.call_args[1]["msg"]
        assert "Redis error during rate limit reset." in logged_msg


# =========================== HIT METHOD ============================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "strategy",
    [
        LimitingStrategy.MOVING_WINDOW,
        LimitingStrategy.FIXED_WINDOW,
        LimitingStrategy.SLIDING_WINDOW,
    ],
)
async def test_limiter_hit_no_value(strategy):
    """Test hit returns True immediately if value is None (no rate limit defined)."""
    mock_redis_pool = MagicMock()
    mock_redis_pool.url = "redis://localhost:6379"

    with patch("api.helpers._limiter.storage.RedisStorage") as MockStorage, patch("api.helpers._limiter.Redis") as MockRedis:
        MockStorage.return_value = AsyncMock(spec=RedisStorage)
        MockRedis.return_value = AsyncMock()

        limiter = Limiter(mock_redis_pool, strategy=strategy)

        result = await limiter.hit(user_id=1, router_id=1, type=LimitType.RPM, value=None)
        assert result is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "strategy",
    [
        LimitingStrategy.MOVING_WINDOW,
        LimitingStrategy.FIXED_WINDOW,
        LimitingStrategy.SLIDING_WINDOW,
    ],
)
@pytest.mark.parametrize(
    "limit_type, expected_limit_class_name, granularity",
    [
        (LimitType.TPM, "RateLimitItemPerMinute", "minute"),
        (LimitType.TPD, "RateLimitItemPerDay", "day"),
        (LimitType.RPM, "RateLimitItemPerMinute", "minute"),
        (LimitType.RPD, "RateLimitItemPerDay", "day"),
    ],
)
async def test_limiter_hit_types(strategy, limit_type, expected_limit_class_name, granularity):
    """Test hit with different limit types creates correct limit items."""
    mock_redis_pool = MagicMock()
    mock_redis_pool.url = "redis://localhost:6379"

    with patch("api.helpers._limiter.storage.RedisStorage") as MockStorage, patch("api.helpers._limiter.Redis") as MockRedis:
        MockStorage.return_value = AsyncMock(spec=RedisStorage)
        MockRedis.return_value = AsyncMock()

        limiter = Limiter(mock_redis_pool, strategy=strategy)
        limiter.strategy.hit = AsyncMock(return_value=True)

        user_id = 99
        router_id = 88
        value = 100
        cost = 5

        result = await limiter.hit(user_id=user_id, router_id=router_id, type=limit_type, value=value, cost=cost)

        args, kwargs = limiter.strategy.hit.call_args
        limit_item = args[0]
        key = args[1]

        assert type(limit_item).__name__ == expected_limit_class_name
        assert limit_item.amount == value

        from api.utils.variables import PREFIX__REDIS_RATE_LIMIT

        assert key == f"{PREFIX__REDIS_RATE_LIMIT}:{limit_type.value}:{user_id}:{router_id}"
        assert kwargs["cost"] == cost
        assert result is True


@pytest.mark.asyncio
@pytest.mark.parametrize("strategy", [LimitingStrategy.MOVING_WINDOW, LimitingStrategy.FIXED_WINDOW, LimitingStrategy.SLIDING_WINDOW])
async def test_limiter_hit_limit_exceeded_with_ttl(strategy):
    """Test hit returns False when limit exceeded and keys have TTL."""
    mock_redis_pool = MagicMock()
    mock_redis_pool.url = "redis://localhost:6379"

    with patch("api.helpers._limiter.storage.RedisStorage") as MockStorage, patch("api.helpers._limiter.Redis") as MockRedis:
        MockStorage.return_value = AsyncMock(spec=RedisStorage)
        mock_internal_redis = AsyncMock()
        MockRedis.return_value = mock_internal_redis

        limiter = Limiter(mock_redis_pool, strategy)
        limiter.strategy.hit = AsyncMock(return_value=False)

        mock_internal_redis.ttl.return_value = 10

        result = await limiter.hit(1, 1, LimitType.RPM, 100)

        assert result is False
        mock_internal_redis.delete.assert_not_called()
        mock_internal_redis.reset.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("strategy", [LimitingStrategy.MOVING_WINDOW, LimitingStrategy.FIXED_WINDOW, LimitingStrategy.SLIDING_WINDOW])
async def test_limiter_hit_limit_exceeded_no_ttl_cleanup(strategy):
    """Test cleanup when TTLs are missing (-1)."""
    mock_redis_pool = MagicMock()
    mock_redis_pool.url = "redis://localhost:6379"

    with (
        patch("api.helpers._limiter.storage.RedisStorage") as MockStorage,
        patch("api.helpers._limiter.Redis") as MockRedis,
        patch("api.helpers._limiter.logger") as mock_logger,
    ):
        MockStorage.return_value = AsyncMock(spec=RedisStorage)
        mock_internal_redis = AsyncMock()
        mock_internal_redis.ttl.return_value = -1
        MockRedis.return_value = mock_internal_redis

        limiter = Limiter(mock_redis_pool, strategy)
        limiter.strategy.hit = AsyncMock(return_value=True)

        user_id = 1
        router_id = 2
        value = 50
        limit_type = LimitType.RPM

        await limiter.hit(user_id, router_id, limit_type, value)

        # Ensure no error occurred
        mock_logger.error.assert_not_called()

        from api.utils.variables import PREFIX__REDIS_RATE_LIMIT

        # example of full Redis key : GET "LIMITS:LIMITER/ogl_rt:rpd:1:1/1000000/1/day"
        key = f"{PREFIX__REDIS_RATE_LIMIT}:{limit_type.value}:{user_id}:{router_id}"
        granularity = "minute"
        real_key = f"LIMITS:LIMITER/{key}/{value}/1/{granularity}"

        assert call(real_key) in mock_internal_redis.ttl.call_args_list
        assert call(real_key) in mock_internal_redis.delete.call_args_list


@pytest.mark.asyncio
@pytest.mark.parametrize("strategy", [LimitingStrategy.MOVING_WINDOW, LimitingStrategy.FIXED_WINDOW, LimitingStrategy.SLIDING_WINDOW])
async def test_limiter_hit_exception(strategy):
    """Test fail-open behavior on exception."""
    mock_redis_pool = MagicMock()
    mock_redis_pool.url = "redis://localhost:6379"

    with (
        patch("api.helpers._limiter.storage.RedisStorage") as MockStorage,
        patch("api.helpers._limiter.Redis") as MockRedis,
        patch("api.helpers._limiter.logger") as mock_logger,
    ):
        MockStorage.return_value = AsyncMock(spec=RedisStorage)
        MockRedis.return_value = AsyncMock()

        limiter = Limiter(mock_redis_pool, strategy)

        limiter.strategy.hit = AsyncMock(side_effect=Exception("Boom"))

        result = await limiter.hit(1, 1, LimitType.RPM, 100)

        assert result is True
        mock_logger.error.assert_called_once()
        logged_msg = mock_logger.error.call_args[1]["msg"]
        assert "Error during rate limit hit." in logged_msg


# =========================== RESET METHOD ============================


@pytest.mark.asyncio
@pytest.mark.parametrize("strategy", [LimitingStrategy.MOVING_WINDOW, LimitingStrategy.FIXED_WINDOW, LimitingStrategy.SLIDING_WINDOW])
async def test_limiter_remaining_early_return(strategy):
    """Test remaining returns None immediately if value is None."""
    mock_redis_pool = MagicMock()
    mock_redis_pool.url = "redis://localhost:6379"

    with patch("api.helpers._limiter.storage.RedisStorage") as MockStorage, patch("api.helpers._limiter.Redis") as MockRedis:
        MockStorage.return_value = AsyncMock(spec=RedisStorage)
        MockRedis.return_value = AsyncMock()

        limiter = Limiter(mock_redis_pool, strategy)

        result = await limiter.remaining(user_id=1, router_id=1, type=LimitType.RPM, value=None)

        assert result is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "limit_type, expected_limit_class_name, granularity",
    [
        (LimitType.TPM, "RateLimitItemPerMinute", "minute"),
        (LimitType.TPD, "RateLimitItemPerDay", "day"),
        (LimitType.RPM, "RateLimitItemPerMinute", "minute"),
        (LimitType.RPD, "RateLimitItemPerDay", "day"),
    ],
)
@pytest.mark.parametrize("strategy", [LimitingStrategy.MOVING_WINDOW, LimitingStrategy.FIXED_WINDOW, LimitingStrategy.SLIDING_WINDOW])
async def test_limiter_remaining_success(limit_type, expected_limit_class_name, granularity, strategy):
    """Test remaining returns correct window stats."""
    mock_redis_pool = MagicMock()
    mock_redis_pool.url = "redis://localhost:6379"

    with patch("api.helpers._limiter.storage.RedisStorage") as MockStorage, patch("api.helpers._limiter.Redis") as MockRedis:
        MockStorage.return_value = AsyncMock(spec=RedisStorage)
        MockRedis.return_value = AsyncMock()

        limiter = Limiter(mock_redis_pool, strategy)

        # Mock strategy.get_window_stats
        mock_window_stats = MagicMock()
        mock_window_stats.remaining = 42
        limiter.strategy.get_window_stats = AsyncMock(return_value=mock_window_stats)

        user_id = 123
        router_id = 456
        value = 1000

        result = await limiter.remaining(user_id=user_id, router_id=router_id, type=limit_type, value=value)

        assert result == 42

        # Verify strategy.get_window_stats call
        args, _ = limiter.strategy.get_window_stats.call_args
        limit_item = args[0]
        key = args[1]

        assert type(limit_item).__name__ == expected_limit_class_name
        assert limit_item.amount == value

        from api.utils.variables import PREFIX__REDIS_RATE_LIMIT

        assert key == f"{PREFIX__REDIS_RATE_LIMIT}:{limit_type.value}:{user_id}:{router_id}"


@pytest.mark.asyncio
@pytest.mark.parametrize("strategy", [LimitingStrategy.MOVING_WINDOW, LimitingStrategy.FIXED_WINDOW, LimitingStrategy.SLIDING_WINDOW])
async def test_limiter_remaining_exception(strategy):
    """Test exception handling in remaining."""
    mock_redis_pool = MagicMock()
    mock_redis_pool.url = "redis://localhost:6379"

    with (
        patch("api.helpers._limiter.storage.RedisStorage") as MockStorage,
        patch("api.helpers._limiter.Redis") as MockRedis,
        patch("api.helpers._limiter.logger") as mock_logger,
    ):
        MockStorage.return_value = AsyncMock(spec=RedisStorage)
        MockRedis.return_value = AsyncMock()

        limiter = Limiter(mock_redis_pool, strategy)

        limiter.strategy.get_window_stats = AsyncMock(side_effect=Exception("DB Error"))

        result = await limiter.remaining(user_id=1, router_id=1, type=LimitType.RPM, value=100)

        assert result is None
        mock_logger.debug.assert_called()


# =========================== CHECK USER LIMITS METHOD ============================


@pytest.mark.asyncio
@pytest.mark.parametrize("strategy", [LimitingStrategy.MOVING_WINDOW, LimitingStrategy.FIXED_WINDOW, LimitingStrategy.SLIDING_WINDOW])
async def test_limiter_check_user_limits_admin(strategy):
    """Test admin (id=0) bypasses all checks."""
    mock_redis_pool = MagicMock()
    mock_redis_pool.url = "redis://localhost:6379"

    with patch("api.helpers._limiter.storage.RedisStorage") as MockStorage, patch("api.helpers._limiter.Redis") as MockRedis:
        MockStorage.return_value = AsyncMock(spec=RedisStorage)
        MockRedis.return_value = AsyncMock()

        limiter = Limiter(mock_redis_pool, strategy)
        limiter.hit = AsyncMock(return_value=True)

        user_info = UserInfo(id=0, email="admin@test.com", name="Admin", permissions=[], limits=[], expires=None, created=0, updated=0)

        await limiter.check_user_limits(user_info=user_info, router_id=1)

        limiter.hit.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("strategy", [LimitingStrategy.MOVING_WINDOW, LimitingStrategy.FIXED_WINDOW, LimitingStrategy.SLIDING_WINDOW])
async def test_limiter_check_user_limits_no_access(strategy):
    """Test raises ModelNotFoundException when checks fail router access."""
    mock_redis_pool = MagicMock()
    mock_redis_pool.url = "redis://localhost:6379"

    with patch("api.helpers._limiter.storage.RedisStorage") as MockStorage, patch("api.helpers._limiter.Redis") as MockRedis:
        MockStorage.return_value = AsyncMock(spec=RedisStorage)
        MockRedis.return_value = AsyncMock()

        limiter = Limiter(mock_redis_pool, strategy)

        # User limits do not contain router_id=999
        user_info = UserInfo(id=1, email="u@test.com", name="User", permissions=[], limits=[], expires=None, created=0, updated=0)

        with pytest.raises(ModelNotFoundException):
            await limiter.check_user_limits(user_info=user_info, router_id=999)


@pytest.mark.asyncio
@pytest.mark.parametrize("strategy", [LimitingStrategy.MOVING_WINDOW, LimitingStrategy.FIXED_WINDOW, LimitingStrategy.SLIDING_WINDOW])
async def test_limiter_check_user_limits_insufficient_permission(strategy):
    """Test raises InsufficientPermissionException when any limit value is 0."""
    mock_redis_pool = MagicMock()
    mock_redis_pool.url = "redis://localhost:6379"

    with patch("api.helpers._limiter.storage.RedisStorage") as MockStorage, patch("api.helpers._limiter.Redis") as MockRedis:
        MockStorage.return_value = AsyncMock(spec=RedisStorage)
        MockRedis.return_value = AsyncMock()

        limiter = Limiter(mock_redis_pool, strategy)

        # Mock limit with 0 value
        limit_mock = Limit(router=1, type=LimitType.TPM, value=0)

        user_info = UserInfo(id=1, email="u@test.com", name="User", permissions=[], limits=[limit_mock], expires=None, created=0, updated=0)

        with pytest.raises(InsufficientPermissionException):
            await limiter.check_user_limits(user_info=user_info, router_id=1)


@pytest.mark.asyncio
@pytest.mark.parametrize("strategy", [LimitingStrategy.MOVING_WINDOW, LimitingStrategy.FIXED_WINDOW, LimitingStrategy.SLIDING_WINDOW])
async def test_limiter_check_user_limits_rpm_exceeded(strategy):
    """Test raises RateLimitExceeded when RPM limit is hit."""
    mock_redis_pool = MagicMock()
    mock_redis_pool.url = "redis://localhost:6379"

    with patch("api.helpers._limiter.storage.RedisStorage") as MockStorage, patch("api.helpers._limiter.Redis") as MockRedis:
        MockStorage.return_value = AsyncMock(spec=RedisStorage)
        MockRedis.return_value = AsyncMock()

        limiter = Limiter(mock_redis_pool, strategy)

        # Mock limits
        limits = [
            Limit(router=1, type=LimitType.RPM, value=10),
            Limit(router=1, type=LimitType.RPD, value=1000),
            Limit(router=1, type=LimitType.TPM, value=500),
            Limit(router=1, type=LimitType.TPD, value=5000),
        ]

        user_info = UserInfo(id=1, email="u@test.com", name="User", permissions=[], limits=limits, expires=None, created=0, updated=0)

        # Mock hit/remaining
        # hit returns False for RPM check (first call is RPM check)
        # Sequence of calls: hit(RPM), hit(RPD), [hit(TPM), hit(TPD)]
        # We need to simulate hit call for RPM returning False

        # Using side_effect to return False for specific call is safer
        async def hit_side_effect(user_id, router_id, type, value, cost=1):
            if type == LimitType.RPM:
                return False
            return True

        limiter.hit = AsyncMock(side_effect=hit_side_effect)
        limiter.remaining = AsyncMock(return_value=0)

        with pytest.raises(RateLimitExceeded) as exc_info:
            await limiter.check_user_limits(user_info=user_info, router_id=1)

        assert "requests per minute exceeded" in str(exc_info.value.detail)


@pytest.mark.asyncio
@pytest.mark.parametrize("strategy", [LimitingStrategy.MOVING_WINDOW, LimitingStrategy.FIXED_WINDOW, LimitingStrategy.SLIDING_WINDOW])
async def test_limiter_check_user_limits_with_prompt_tokens_success(strategy):
    """Test success path with prompt tokens."""
    mock_redis_pool = MagicMock()
    mock_redis_pool.url = "redis://localhost:6379"

    with patch("api.helpers._limiter.storage.RedisStorage") as MockStorage, patch("api.helpers._limiter.Redis") as MockRedis:
        MockStorage.return_value = AsyncMock(spec=RedisStorage)
        MockRedis.return_value = AsyncMock()

        limiter = Limiter(mock_redis_pool, strategy)

        # Mock limits: RPM, RPD, TPM, TPD
        # We need at least one limit for router 1 so has_access=True
        limit_rpm = Limit(router=1, type=LimitType.RPM, value=100)

        user_info = UserInfo(id=1, email="u@test.com", name="User", permissions=[], limits=[limit_rpm], expires=None, created=0, updated=0)

        limiter.hit = AsyncMock(return_value=True)

        limits = [
            Limit(router=1, type=LimitType.RPM, value=100),
            Limit(router=1, type=LimitType.RPD, value=1000),
            Limit(router=1, type=LimitType.TPM, value=500),
            Limit(router=1, type=LimitType.TPD, value=5000),
        ]
        user_info = UserInfo(id=1, email="u@test.com", name="User", permissions=[], limits=limits, expires=None, created=0, updated=0)

        limiter.hit = AsyncMock(return_value=True)

        await limiter.check_user_limits(user_info=user_info, router_id=1, prompt_tokens=50)

        called_types = [call.kwargs["type"] for call in limiter.hit.call_args_list]
        assert LimitType.RPM in called_types
        assert LimitType.RPD in called_types
        assert LimitType.TPM in called_types
        assert LimitType.TPD in called_types


@pytest.mark.asyncio
@pytest.mark.parametrize("strategy", [LimitingStrategy.MOVING_WINDOW, LimitingStrategy.FIXED_WINDOW, LimitingStrategy.SLIDING_WINDOW])
async def test_limiter_check_user_limits_rpd_exceeded(strategy):
    """Test raises RateLimitExceeded when RPD limit is hit."""
    mock_redis_pool = MagicMock()
    mock_redis_pool.url = "redis://localhost:6379"

    with patch("api.helpers._limiter.storage.RedisStorage") as MockStorage, patch("api.helpers._limiter.Redis") as MockRedis:
        MockStorage.return_value = AsyncMock(spec=RedisStorage)
        MockRedis.return_value = AsyncMock()

        limiter = Limiter(mock_redis_pool, strategy)

        limits = [
            Limit(router=1, type=LimitType.RPM, value=100),
            Limit(router=1, type=LimitType.RPD, value=1000),
            Limit(router=1, type=LimitType.TPM, value=500),
            Limit(router=1, type=LimitType.TPD, value=5000),
        ]
        user_info = UserInfo(id=1, email="u@test.com", name="User", permissions=[], limits=limits, expires=None, created=0, updated=0)

        async def hit_side_effect(user_id, router_id, type, value, cost=1):
            if type == LimitType.RPD:
                return False
            return True

        limiter.hit = AsyncMock(side_effect=hit_side_effect)
        limiter.remaining = AsyncMock(return_value=0)

        with pytest.raises(RateLimitExceeded) as exc_info:
            await limiter.check_user_limits(user_info=user_info, router_id=1)

        assert "requests per day exceeded" in str(exc_info.value.detail)


@pytest.mark.asyncio
@pytest.mark.parametrize("strategy", [LimitingStrategy.MOVING_WINDOW, LimitingStrategy.FIXED_WINDOW, LimitingStrategy.SLIDING_WINDOW])
async def test_limiter_check_user_limits_tpd_exceeded(strategy):
    """Test raises RateLimitExceeded when TPD limit is hit."""
    mock_redis_pool = MagicMock()
    mock_redis_pool.url = "redis://localhost:6379"

    with patch("api.helpers._limiter.storage.RedisStorage") as MockStorage, patch("api.helpers._limiter.Redis") as MockRedis:
        MockStorage.return_value = AsyncMock(spec=RedisStorage)
        MockRedis.return_value = AsyncMock()
        limiter = Limiter(mock_redis_pool, strategy)

        limits = [
            Limit(router=1, type=LimitType.RPM, value=100),
            Limit(router=1, type=LimitType.RPD, value=1000),
            Limit(router=1, type=LimitType.TPM, value=500),
            Limit(router=1, type=LimitType.TPD, value=5000),
        ]
        user_info = UserInfo(id=1, email="u@test.com", name="User", permissions=[], limits=limits, expires=None, created=0, updated=0)

        async def hit_side_effect(user_id, router_id, type, value, cost=1):
            if type == LimitType.TPD:
                return False
            return True

        limiter.hit = AsyncMock(side_effect=hit_side_effect)
        limiter.remaining = AsyncMock(return_value=0)

        with pytest.raises(RateLimitExceeded) as exc_info:
            await limiter.check_user_limits(user_info=user_info, router_id=1, prompt_tokens=100)

        assert "input tokens per day exceeded" in str(exc_info.value.detail)
