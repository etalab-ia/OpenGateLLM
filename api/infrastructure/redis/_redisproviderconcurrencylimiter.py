import asyncio
import logging
import random

from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import RedisError

from api.domain.provider._providerconcurrencylimiter import (
    ProviderConcurrencyLimiter,
    ProviderReservation,
    ProviderReservationRefused,
    ProviderReservationResult,
)
from api.domain.provider.entities import Provider
from api.domain.router.entities import RouterLoadBalancingStrategy

logger = logging.getLogger(__name__)

# Each provider has a sorted set holding one entry per request in progress. The entry's score is the time (in ms) after
# which it counts as abandoned, so a worker that dies without releasing its place frees it once that time has passed.
#
# Counting the load and writing the reservation run as one script, so two requests cannot both take the last place.
#
# KEYS[1]  the provider's sorted set
# ARGV     request id, limit (-1 when the limit is not enforced), lifetime of the reservation in ms
# Returns  1 when the place is reserved, 0 when the provider is full.
TRY_RESERVE_SCRIPT = """
local time = redis.call("TIME")
local now_ms = time[1] * 1000 + math.floor(time[2] / 1000)
redis.call("ZREMRANGEBYSCORE", KEYS[1], "-inf", now_ms)

local limit = tonumber(ARGV[2])
if limit >= 0 and redis.call("ZCARD", KEYS[1]) >= limit then
    return 0
end

redis.call("ZADD", KEYS[1], now_ms + tonumber(ARGV[3]), ARGV[1])
return 1
"""


class RedisProviderConcurrencyLimiter(ProviderConcurrencyLimiter):
    LOAD_KEY_PREFIX = "ogl_qos:load"
    RESERVATION_TTL_MILLISECONDS = 30_000
    HEARTBEAT_INTERVAL_SECONDS = 10.0
    NO_LIMIT = -1

    def __init__(self, redis_client: AsyncRedis):
        self.redis_client = redis_client
        self._try_reserve = redis_client.register_script(TRY_RESERVE_SCRIPT)
        self._heartbeats: dict[str, asyncio.Task] = {}

    async def reserve(
        self,
        request_id: str,
        providers: list[Provider],
        strategy: RouterLoadBalancingStrategy,
        enforce_limit: bool,
    ) -> ProviderReservationResult:
        open_providers = [provider for provider in providers if provider.qos_limit != 0]

        for provider in await self._order_by_strategy(providers=open_providers, strategy=strategy):
            limit = provider.qos_limit if enforce_limit and provider.qos_limit is not None else self.NO_LIMIT
            key = self._load_key(provider.id)
            if await self._try_reserve(keys=[key], args=[request_id, limit, self.RESERVATION_TTL_MILLISECONDS], client=self.redis_client):
                self._heartbeats[request_id] = asyncio.create_task(
                    self._heartbeat(key=key, request_id=request_id), name=f"reservation-heartbeat-{request_id}"
                )
                return ProviderReservation(provider=provider, request_id=request_id)

        return ProviderReservationRefused()

    async def _order_by_strategy(self, providers: list[Provider], strategy: RouterLoadBalancingStrategy) -> list[Provider]:
        if strategy == RouterLoadBalancingStrategy.SHUFFLE:
            return random.sample(providers, k=len(providers))

        loads = await self._read_loads(providers=providers)

        if any(provider.qos_limit is None for provider in providers):
            return sorted(providers, key=lambda provider: (loads[provider.id], provider.id))

        return sorted(providers, key=lambda provider: (-(provider.qos_limit - loads[provider.id]), provider.id))

    async def _read_loads(self, providers: list[Provider]) -> dict[int, int]:
        now_ms = self._milliseconds(await self.redis_client.time())
        pipeline = self.redis_client.pipeline(transaction=False)
        for provider in providers:
            pipeline.zcount(self._load_key(provider.id), f"({now_ms}", "+inf")
        loads = await pipeline.execute()
        return {provider.id: int(load) for provider, load in zip(providers, loads)}

    async def _heartbeat(self, key: str, request_id: str) -> None:
        while True:
            await asyncio.sleep(self.HEARTBEAT_INTERVAL_SECONDS)
            try:
                now_ms = self._milliseconds(await self.redis_client.time())
                await self.redis_client.zadd(key, {request_id: now_ms + self.RESERVATION_TTL_MILLISECONDS}, xx=True)
            except RedisError:
                logger.warning("Failed to renew the provider reservation of request %s.", request_id)

    async def release(self, reservation: ProviderReservation) -> None:
        heartbeat = self._heartbeats.pop(reservation.request_id, None)
        if heartbeat is not None:
            heartbeat.cancel()
            await asyncio.wait([heartbeat])

        try:
            await self.redis_client.zrem(self._load_key(reservation.provider.id), reservation.request_id)
        except RedisError:
            logger.exception("Failed to release the provider reservation of request %s.", reservation.request_id)

    @classmethod
    def _load_key(cls, provider_id: int) -> str:
        return f"{cls.LOAD_KEY_PREFIX}:{provider_id}"

    @staticmethod
    def _milliseconds(redis_time: tuple[int, int]) -> int:
        seconds, microseconds = redis_time
        return seconds * 1000 + microseconds // 1000
