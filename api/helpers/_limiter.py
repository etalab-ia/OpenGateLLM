import logging
import traceback

from limits import RateLimitItemPerDay, RateLimitItemPerMinute
from limits.aio import storage, strategies
from redis.asyncio import ConnectionPool, Redis, RedisError

from api.schemas.admin.roles import LimitType
from api.schemas.core.configuration import LimitingStrategy
from api.schemas.me.info import UserInfo
from api.utils.exceptions import InsufficientPermissionException, ModelNotFoundException, RateLimitExceeded
from api.utils.variables import PREFIX__REDIS_RATE_LIMIT

logger = logging.getLogger(__name__)


class Limiter:
    def __init__(self, redis_pool: ConnectionPool, strategy: LimitingStrategy):
        self.redis_pool = redis_pool
        self.redis_client = storage.RedisStorage(uri=self.redis_pool.url, connection_pool=self.redis_pool, implementation="redispy")
        self.redis = Redis.from_url(url=self.redis_pool.url)

        if strategy == LimitingStrategy.MOVING_WINDOW:
            self.strategy = strategies.MovingWindowRateLimiter(storage=self.redis_client)
        elif strategy == LimitingStrategy.FIXED_WINDOW:
            self.strategy = strategies.FixedWindowRateLimiter(storage=self.redis_client)
        else:  # SLIDING_WINDOW
            self.strategy = strategies.SlidingWindowCounterRateLimiter(storage=self.redis_client)

    async def reset(self) -> None:
        """
        Reset the limits when starting the API.
        """
        try:
            await self.redis_client.reset()
        except RedisError:
            logger.error(msg="Redis error during rate limit reset.", exc_info=True)

    async def hit(self, user_id: int, router_id: int, type: LimitType, value: int | None = None, cost: int = 1) -> bool | None:
        """
        Check if the user has reached the limit for the given type and router.

        Args:
            user_id(int): The user ID to check the limit for.
            router_id (int): The router ID to check the limit for.
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

            key = f"{PREFIX__REDIS_RATE_LIMIT}:{type.value}:{user_id}:{router_id}"
            result = await self.strategy.hit(limit, key, cost=cost)

            if not result:
                res = await self.redis.ttl(key)
                if res == -1:
                    await self.redis.delete(key)

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

            window = await self.strategy.get_window_stats(limit, f"{PREFIX__REDIS_RATE_LIMIT}:{type.value}:{user_id}:{router_id}")
            return window.remaining

        except Exception:
            logger.error(msg="Error during rate limit remaining.")
            logger.error(msg=traceback.format_exc())

    async def check_user_limits(self, user_info: UserInfo, router_id: int, prompt_tokens: int | None = None) -> None:
        if user_info.id == 0:
            return

        has_access = False
        tpm, tpd, rpm, rpd = 0, 0, 0, 0
        for limit in user_info.limits:
            if limit.router == router_id:
                has_access = True
                if limit.type == LimitType.TPM:
                    tpm = limit.value
                elif limit.type == LimitType.TPD:
                    tpd = limit.value
                elif limit.type == LimitType.RPM:
                    rpm = limit.value
                elif limit.type == LimitType.RPD:
                    rpd = limit.value

        if not has_access:
            raise ModelNotFoundException()

        if 0 in [tpm, tpd, rpm, rpd]:
            raise InsufficientPermissionException(detail="Insufficient permissions to access the model.")

        # RPM
        check = await self.hit(user_id=user_info.id, router_id=router_id, type=LimitType.RPM, value=rpm)
        if not check:
            remaining = await self.remaining(user_id=user_info.id, router_id=router_id, type=LimitType.RPM, value=rpm)
            raise RateLimitExceeded(detail=f"{str(rpm)} requests per minute exceeded (remaining: {remaining}).")

        # RPD
        check = await self.hit(user_id=user_info.id, router_id=router_id, type=LimitType.RPD, value=rpd)
        if not check:
            remaining = await self.remaining(user_id=user_info.id, router_id=router_id, type=LimitType.RPD, value=rpd)
            raise RateLimitExceeded(detail=f"{str(rpd)} requests per day exceeded (remaining: {remaining}).")

        if not prompt_tokens:
            return

        # TPM
        check = await self.hit(user_id=user_info.id, router_id=router_id, type=LimitType.TPM, value=tpm, cost=prompt_tokens)
        if not check:
            remaining = await self.remaining(user_id=user_info.id, router_id=router_id, type=LimitType.TPM, value=tpm)
            raise RateLimitExceeded(detail=f"{str(tpm)} input tokens per minute exceeded (remaining: {remaining}).")

        # TPD
        check = await self.hit(user_id=user_info.id, router_id=router_id, type=LimitType.TPD, value=tpd, cost=prompt_tokens)
        if not check:
            remaining = await self.remaining(user_id=user_info.id, router_id=router_id, type=LimitType.TPD, value=tpd)
            raise RateLimitExceeded(detail=f"{str(tpd)} input tokens per day exceeded (remaining: {remaining}).")
