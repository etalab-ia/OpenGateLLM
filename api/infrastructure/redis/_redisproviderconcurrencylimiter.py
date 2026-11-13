import asyncio
import logging
from typing import ClassVar

from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import RedisError

from api.domain.provider._providerconcurrencylimiter import (
    ProviderConcurrencyLimiter,
    ProviderLimitsCannotBeEnforced,
    ProviderReservation,
    ProviderReservationRefused,
)
from api.domain.provider.entities import Provider, ProviderLoads

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

    _redis_is_unreachable: ClassVar[bool] = False
    _requests_forwarded_without_applying_qos: ClassVar[int] = 0

    def __init__(self, redis_client: AsyncRedis):
        self.redis_client = redis_client
        self._try_reserve = redis_client.register_script(TRY_RESERVE_SCRIPT)
        self._heartbeats: dict[str, asyncio.Task] = {}

    async def read_loads(self, providers: list[Provider]) -> ProviderLoads | ProviderLimitsCannotBeEnforced:
        try:
            now_ms = self._milliseconds(await self.redis_client.time())
            pipeline = self.redis_client.pipeline(transaction=False)
            for provider in providers:
                pipeline.zcount(self._load_key(provider.id), f"({now_ms}", "+inf")
            loads = await pipeline.execute()
        except RedisError:
            self._record_redis_outage()
            return ProviderLimitsCannotBeEnforced()

        self._record_redis_recovery()
        return ProviderLoads(load_by_provider_id={provider.id: int(load) for provider, load in zip(providers, loads)})

    async def reserve(
        self, request_id: str, provider: Provider, limit: int | None
    ) -> ProviderReservation | ProviderReservationRefused | ProviderLimitsCannotBeEnforced:
        provider_load_key = self._load_key(provider.id)
        try:
            reserved = await self._try_reserve(
                keys=[provider_load_key],
                args=[request_id, self.NO_LIMIT if limit is None else limit, self.RESERVATION_TTL_MILLISECONDS],
                client=self.redis_client,
            )
        except RedisError:
            self._record_redis_outage()
            return ProviderLimitsCannotBeEnforced()

        self._record_redis_recovery()
        if not reserved:
            return ProviderReservationRefused()

        self._heartbeats[request_id] = asyncio.create_task(
            self._heartbeat(key=provider_load_key, request_id=request_id), name=f"reservation-heartbeat-{request_id}"
        )
        return ProviderReservation(provider=provider, request_id=request_id)

    async def _heartbeat(self, key: str, request_id: str) -> None:
        while True:
            await asyncio.sleep(self.HEARTBEAT_INTERVAL_SECONDS)
            try:
                now_ms = self._milliseconds(await self.redis_client.time())
                await self.redis_client.zadd(key, {request_id: now_ms + self.RESERVATION_TTL_MILLISECONDS}, xx=True)
            except RedisError:
                level = logging.DEBUG if self._redis_is_unreachable else logging.WARNING
                logger.log(level, "Failed to renew the provider reservation of request %s.", request_id)

    @classmethod
    def _record_redis_outage(cls) -> None:
        if not cls._redis_is_unreachable:
            logger.exception("Redis is unreachable: provider limits are no longer enforced.")
            cls._redis_is_unreachable = True
        cls._requests_forwarded_without_applying_qos += 1

    @classmethod
    def _record_redis_recovery(cls) -> None:
        if cls._redis_is_unreachable:
            logger.info("Redis is reachable again: %s requests were forwarded without provider limits.", cls._requests_forwarded_without_applying_qos)
            cls._redis_is_unreachable = False
            cls._requests_forwarded_without_applying_qos = 0

    async def release(self, reservation: ProviderReservation) -> None:
        heartbeat = self._heartbeats.pop(reservation.request_id, None)
        if heartbeat is None:
            return

        heartbeat.cancel()

        try:
            await self.redis_client.zrem(self._load_key(reservation.provider.id), reservation.request_id)
        except RedisError:
            level = logging.DEBUG if self._redis_is_unreachable else logging.ERROR
            logger.log(level, "Failed to release the provider reservation of request %s.", reservation.request_id, exc_info=True)

        await asyncio.wait([heartbeat])

    async def wait_for_capacity(self, seconds: float) -> None:
        await asyncio.sleep(seconds)

    @classmethod
    def _load_key(cls, provider_id: int) -> str:
        return f"{cls.LOAD_KEY_PREFIX}:{provider_id}"

    @staticmethod
    def _milliseconds(redis_time: tuple[int, int]) -> int:
        seconds, microseconds = redis_time
        return seconds * 1000 + microseconds // 1000
