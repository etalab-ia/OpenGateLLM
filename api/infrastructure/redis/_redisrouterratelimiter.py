import logging

from limits import RateLimitItemPerDay, RateLimitItemPerMinute
from limits.aio import storage, strategies
from limits.util import WindowStats
from redis.asyncio import ConnectionPool, Redis, RedisError

from api.domain.role.entities import Limit, LimitType
from api.domain.router import RouterRateLimiter
from api.domain.router.entities import RouterRateLimitState, RpdRateLimitState, RpmRateLimitState, TpdRateLimitState, TpmRateLimitState
from api.schemas.core.configuration import LimitingStrategy
from api.utils.variables import PREFIX__REDIS_RATE_LIMIT

logger = logging.getLogger(__name__)


class RedisRouterRateLimiter(RouterRateLimiter):
    def __init__(self, redis_pool: ConnectionPool, strategy: LimitingStrategy):
        self.redis_pool = redis_pool
        self.redis_storage = storage.RedisStorage(uri=self.redis_pool.url, connection_pool=self.redis_pool, implementation="redispy")
        self.redis_client = Redis(connection_pool=redis_pool)

        match strategy:
            case LimitingStrategy.MOVING_WINDOW:
                self.strategy = strategies.MovingWindowRateLimiter(storage=self.redis_storage)
            case LimitingStrategy.FIXED_WINDOW:
                self.strategy = strategies.FixedWindowRateLimiter(storage=self.redis_storage)
            case LimitingStrategy.SLIDING_WINDOW:
                self.strategy = strategies.SlidingWindowCounterRateLimiter(storage=self.redis_storage)

    async def get_rate_limit_state(self, user_id: int, router_limits: list[Limit], router_id: int) -> RouterRateLimitState:
        state = RouterRateLimitState(rpm=RpmRateLimitState(), rpd=RpdRateLimitState(), tpm=TpmRateLimitState(), tpd=TpdRateLimitState())

        for limit in router_limits:
            match limit.type:
                case LimitType.RPM:
                    state.rpm.value = limit.value
                    if not limit.value:
                        continue
                    window = await self._get_window_stats(user_id=user_id, router_id=router_id, type=LimitType.RPM, value=limit.value)
                    state.rpm.remaining = window.remaining
                    state.rpm.reset = window.reset_time

                case LimitType.RPD:
                    state.rpd.value = limit.value
                    if not limit.value:
                        continue
                    window = await self._get_window_stats(user_id=user_id, router_id=router_id, type=LimitType.RPD, value=limit.value)
                    state.rpd.remaining = window.remaining
                    state.rpd.reset = window.reset_time

                case LimitType.TPM:
                    state.tpm.value = limit.value
                    if not limit.value:
                        continue
                    window = await self._get_window_stats(user_id=user_id, router_id=router_id, type=LimitType.TPM, value=limit.value)
                    state.tpm.remaining = window.remaining
                    state.tpm.reset = window.reset_time

                case LimitType.TPD:
                    state.tpd.value = limit.value
                    if not limit.value:
                        continue
                    window = await self._get_window_stats(user_id=user_id, router_id=router_id, type=LimitType.TPD, value=limit.value)
                    state.tpd.remaining = window.remaining
                    state.tpd.reset = window.reset_time

        return state

    async def update_rate_limit_state(self, user_id: int, router_limits: list[Limit], router_id: int, prompt_tokens: int) -> None:
        rpm = next((limit.value for limit in router_limits if limit.type == LimitType.RPM), 0)
        await self._hit(user_id=user_id, router_id=router_id, type=LimitType.RPM, value=rpm)

        rpd = next((limit.value for limit in router_limits if limit.type == LimitType.RPD), 0)
        await self._hit(user_id=user_id, router_id=router_id, type=LimitType.RPD, value=rpd)

        if not prompt_tokens:
            return

        tpm = next((limit.value for limit in router_limits if limit.type == LimitType.TPM), 0)
        await self._hit(user_id=user_id, router_id=router_id, type=LimitType.TPM, value=tpm, cost=prompt_tokens)

        tpd = next((limit.value for limit in router_limits if limit.type == LimitType.TPD), 0)
        await self._hit(user_id=user_id, router_id=router_id, type=LimitType.TPD, value=tpd, cost=prompt_tokens)

    async def reset(self) -> None:
        try:
            await self.redis_storage.reset()
        except RedisError:
            logger.error(msg="Redis error during rate limit reset.", exc_info=True)

    async def _get_limit(self, type: LimitType, value: int | None = None) -> RateLimitItemPerMinute | RateLimitItemPerDay | None:
        if value is None:
            return None

        match type:
            case LimitType.TPM | LimitType.RPM:
                return RateLimitItemPerMinute(amount=value)
            case LimitType.TPD | LimitType.RPD:
                return RateLimitItemPerDay(amount=value)

    async def _get_window_stats(self, user_id: int, router_id: int, type: LimitType, value: int | None = None) -> WindowStats | None:
        try:
            limit = await self._get_limit(type=type, value=value)
            if limit is None:
                return

            key = f"{PREFIX__REDIS_RATE_LIMIT}:{type.value}:{user_id}:{router_id}"
            window = await self.strategy.get_window_stats(limit, key)
            return window

        except Exception:
            logger.error(msg=f"Error during rate limit window stats on key {key}.", exc_info=True)

        return None

    async def _hit(self, user_id: int, router_id: int, type: LimitType, value: int | None = None, cost: int = 1) -> bool:
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

        limit = await self._get_limit(type=type, value=value)
        if limit is None:
            return True

        try:
            key = f"{PREFIX__REDIS_RATE_LIMIT}:{type.value}:{user_id}:{router_id}"
            result = await self.strategy.hit(limit, key, cost=cost)
            if result:
                full_key = f"LIMITS:LIMITER/{key}/{value}/1/{limit.GRANULARITY.name}"
                res = await self.redis_client.ttl(full_key)
                if res == -1:  # no TTL, cleanup
                    await self.redis_client.delete(full_key)
                    return True

            return result

        except Exception:
            logger.error(msg=f"Error during rate limit hit on key {key}.", exc_info=True)

        return True
