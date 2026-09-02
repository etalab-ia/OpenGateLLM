import time

import pytest
from redis.asyncio import Redis as AsyncRedis

from api.domain.role.entities import Limit, LimitType
from api.infrastructure.redis import RedisRouterRateLimiter
from api.schemas.core.configuration import LimitingStrategy


def limits_factory(router_id: int, rpm: int | None = None, rpd: int | None = None, tpm: int | None = None, tpd: int | None = None) -> list[Limit]:
    limits = []
    if rpm is not None:
        limits.append(Limit(router_id=router_id, type=LimitType.RPM, value=rpm))
    if rpd is not None:
        limits.append(Limit(router_id=router_id, type=LimitType.RPD, value=rpd))
    if tpm is not None:
        limits.append(Limit(router_id=router_id, type=LimitType.TPM, value=tpm))
    if tpd is not None:
        limits.append(Limit(router_id=router_id, type=LimitType.TPD, value=tpd))
    return limits


@pytest.fixture
def rate_limiter(test_redis_pool):
    return RedisRouterRateLimiter(redis_pool=test_redis_pool, strategy=LimitingStrategy.MOVING_WINDOW)


@pytest.fixture
def redis_client(test_redis_pool):
    return AsyncRedis(connection_pool=test_redis_pool)


@pytest.mark.asyncio(loop_scope="session")
class TestRedisRouterRateLimiter:
    async def test_get_rate_limit_state_returns_full_remaining_when_no_usage(self, rate_limiter: RedisRouterRateLimiter, redis_client: AsyncRedis):
        # Arrange
        user_id = 1001
        router_id = 2001
        limits = limits_factory(router_id=router_id, rpm=10)

        # Act
        result = await rate_limiter.get_rate_limit_state(user_id=user_id, router_limits=limits, router_id=router_id, prompt_tokens=0)

        # Assert
        assert result.rpm.value == 10
        assert result.rpm.remaining == 10
        assert result.rpm.reset > time.time()

    async def test_get_rate_limit_state_skips_zero_value_limits(self, rate_limiter: RedisRouterRateLimiter):
        # Arrange
        user_id = 1002
        router_id = 2002
        limits = limits_factory(router_id=router_id, rpm=0, tpm=50)

        # Act
        result = await rate_limiter.get_rate_limit_state(user_id=user_id, router_limits=limits, router_id=router_id, prompt_tokens=0)

        # Assert
        assert result.rpm.value == 0
        assert result.rpm.remaining == 0
        assert result.rpm.reset == 0
        assert result.tpm.value == 50
        assert result.tpm.remaining == 50
        assert result.tpm.reset > time.time()
        assert LimitType.RPM.value in result.exceeded_limits(prompt_tokens=0)
        assert LimitType.TPM.value not in result.exceeded_limits(prompt_tokens=0)

    async def test_update_rate_limit_state_decrements_rpm_remaining(self, rate_limiter: RedisRouterRateLimiter):
        # Arrange
        user_id = 1003
        router_id = 2003
        limits = limits_factory(router_id=router_id, rpm=5)

        # Act
        await rate_limiter.update_rate_limit_state(user_id=user_id, router_limits=limits, router_id=router_id, prompt_tokens=0)
        result = await rate_limiter.get_rate_limit_state(user_id=user_id, router_limits=limits, router_id=router_id, prompt_tokens=0)

        # Assert
        assert result.rpm.remaining == 4
        assert result.rpm.reset > time.time()

    async def test_update_rate_limit_state_without_prompt_tokens_does_not_hit_tpm(self, rate_limiter: RedisRouterRateLimiter):
        # Arrange
        user_id = 1004
        router_id = 2004
        limits = limits_factory(router_id=router_id, rpm=10, tpm=100)

        # Act
        await rate_limiter.update_rate_limit_state(user_id=user_id, router_limits=limits, router_id=router_id, prompt_tokens=0)
        result = await rate_limiter.get_rate_limit_state(user_id=user_id, router_limits=limits, router_id=router_id, prompt_tokens=0)

        # Assert
        assert result.rpm.remaining == 9
        assert result.rpm.reset > time.time()
        assert result.tpm.remaining == 100
        assert result.tpm.reset > time.time()

    async def test_update_rate_limit_state_with_prompt_tokens_decrements_tpm_remaining(self, rate_limiter: RedisRouterRateLimiter):
        # Arrange
        user_id = 1005
        router_id = 2005
        limits = limits_factory(router_id=router_id, rpm=10, tpm=50)

        # Act
        await rate_limiter.update_rate_limit_state(user_id=user_id, router_limits=limits, router_id=router_id, prompt_tokens=12)
        result = await rate_limiter.get_rate_limit_state(user_id=user_id, router_limits=limits, router_id=router_id, prompt_tokens=0)

        # Assert
        assert result.tpm.remaining == 38
        assert result.tpm.reset > time.time()

    async def test_multiple_updates_rate_limit_state_decrements_rpm_remaining(self, rate_limiter: RedisRouterRateLimiter):
        # Arrange
        user_id = 1006
        router_id = 2006
        limits = limits_factory(router_id=router_id, rpm=2)

        # Act
        await rate_limiter.update_rate_limit_state(user_id=user_id, router_limits=limits, router_id=router_id, prompt_tokens=0)
        await rate_limiter.update_rate_limit_state(user_id=user_id, router_limits=limits, router_id=router_id, prompt_tokens=0)
        result = await rate_limiter.get_rate_limit_state(user_id=user_id, router_limits=limits, router_id=router_id, prompt_tokens=0)

        # Assert
        assert result.rpm.remaining == 0
        assert result.rpm.reset > time.time()
        assert LimitType.RPM.value in result.exceeded_limits(prompt_tokens=0)

    async def test_get_rate_limit_state_exceeds_tpm_when_prompt_is_larger_than_remaining(self, rate_limiter: RedisRouterRateLimiter):
        # Arrange
        user_id = 1008
        router_id = 2008
        limits = limits_factory(router_id=router_id, rpm=10, tpm=50)
        await rate_limiter.update_rate_limit_state(user_id=user_id, router_limits=limits, router_id=router_id, prompt_tokens=30)

        # Act
        result = await rate_limiter.get_rate_limit_state(user_id=user_id, router_limits=limits, router_id=router_id, prompt_tokens=25)

        # Assert
        assert result.tpm.remaining == 20
        assert LimitType.TPM.value in result.exceeded_limits(prompt_tokens=25)
        assert LimitType.RPM.value not in result.exceeded_limits(prompt_tokens=25)

    async def test_reset_clears_rate_limit_state(self, rate_limiter: RedisRouterRateLimiter, redis_client: AsyncRedis):
        # Arrange
        user_id = 1007
        router_id = 2007
        limits = limits_factory(router_id=router_id, rpm=5)
        await rate_limiter.update_rate_limit_state(user_id=user_id, router_limits=limits, router_id=router_id, prompt_tokens=0)
        assert await redis_client.keys("LIMITS*")

        # Act
        await rate_limiter.reset()
        result = await rate_limiter.get_rate_limit_state(user_id=user_id, router_limits=limits, router_id=router_id, prompt_tokens=0)

        # Assert
        assert await redis_client.keys("LIMITS*") == []
        assert result.rpm.remaining == 5
        assert result.rpm.reset > time.time()
