import logging
import traceback

from limits import RateLimitItemPerDay, RateLimitItemPerMinute
from limits.aio import storage, strategies
from redis.asyncio import ConnectionPool

from api.schemas.admin.roles import LimitType
from api.schemas.core.configuration import LimitingStrategy

logger = logging.getLogger(__name__)


class Limiter:
    def __init__(self, redis_pool: ConnectionPool, strategy: LimitingStrategy):
        self.redis_url = f"redis//:{redis_pool.connection_kwargs.get("password", "")}@{redis_pool.connection_kwargs.get("host", "localhost")}:{redis_pool.connection_kwargs.get("port", 6379)}"
        self.redis_client = storage.RedisStorage(uri=self.redis_url, connection_pool=redis_pool, implementation="redispy")

        if strategy == LimitingStrategy.MOVING_WINDOW:
            self.strategy = strategies.MovingWindowRateLimiter(storage=self.redis_client)
        elif strategy == LimitingStrategy.FIXED_WINDOW:
            self.strategy = strategies.FixedWindowRateLimiter(storage=self.redis_client)
        else:  # SLIDING_WINDOW
            self.strategy = strategies.SlidingWindowCounterRateLimiter(storage=self.redis_client)

    async def hit(self, user_id: int, router_id: int, type: LimitType, value: int | None = None, cost: int = 1) -> bool | None:
        """
        Check if the user has reached the limit for the given type and router.

        Args:
            user_id(int): The user ID to check the limit for.
            model(str): The model to check the limit for.
            type(LimitType): The type of limit to check.
            value(Optional[int]): The value of the limit. If not provided, the limit will be hit.
            cost(int): The cost of the limit, defaults to 1.

        Returns:
            bool: True if the limit has been hit, False otherwise.
        """
        if value is None:
            return True

        try:
            if type == LimitType.TPM:
                limit = RateLimitItemPerMinute(amount=value)
            elif type == LimitType.TPD:
                limit = RateLimitItemPerDay(amount=value)
            elif type == LimitType.RPM:
                limit = RateLimitItemPerMinute(amount=value)
            elif type == LimitType.RPD:
                limit = RateLimitItemPerDay(amount=value)

            result = await self.strategy.hit(limit, f"{type.value}:{user_id}:{router_id}", cost=cost)
            return result

        except Exception:
            logger.error(msg="Error during rate limit hit.", exc_info=True)

        return True

    async def remaining(self, user_id: int, router_id: int, type: LimitType, value: int | None = None) -> int | None:
        if value is None:
            return None

        try:
            if type == LimitType.TPM:
                limit = RateLimitItemPerMinute(amount=value)
            elif type == LimitType.TPD:
                limit = RateLimitItemPerDay(amount=value)
            elif type == LimitType.RPM:
                limit = RateLimitItemPerMinute(amount=value)
            elif type == LimitType.RPD:
                limit = RateLimitItemPerDay(amount=value)

            window = await self.strategy.get_window_stats(limit, f"{type.value}:{user_id}:{router_id}")
            return window.remaining

        except Exception:
            logger.error(msg="Error during rate limit remaining.")
            logger.error(msg=traceback.format_exc())
