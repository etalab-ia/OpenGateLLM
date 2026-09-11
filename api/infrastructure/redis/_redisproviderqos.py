import asyncio
from contextlib import asynccontextmanager, suppress
import logging

from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import RedisError

from api.domain.provider._providerqos import ProviderAdmissionFull, ProviderQoS
from api.domain.provider.entities import Provider
from api.domain.router.entities import RouterLoadBalancingStrategy

logger = logging.getLogger(__name__)

TRY_ADMIT_SCRIPT = """
local request_id = ARGV[1]
local strategy = ARGV[2]
local enforce_limit = ARGV[3] == "1"
local heartbeat_ttl_ms = tonumber(ARGV[4])
local redis_time = redis.call("TIME")
local now_ms = redis_time[1] * 1000 + math.floor(redis_time[2] / 1000)

local eligible = {}
local depth = 0
local any_uncapped = false

for i, key in ipairs(KEYS) do
    local provider_id = tonumber(ARGV[4 + (i - 1) * 2 + 1])
    local raw_limit = ARGV[4 + (i - 1) * 2 + 2]
    local qos_limit = raw_limit == "none" and nil or tonumber(raw_limit)

    redis.call("ZREMRANGEBYSCORE", key, "-inf", now_ms)
    local load = redis.call("ZCARD", key)
    depth = depth + load

    if qos_limit == nil or (qos_limit > 0 and (not enforce_limit or load < qos_limit)) then
        table.insert(eligible, {
            key = key,
            provider_id = provider_id,
            qos_limit = qos_limit,
            load = load
        })
        if qos_limit == nil then
            any_uncapped = true
        end
    end
end

if #eligible == 0 then
    return {"FULL", 0, depth}
end

local selected = eligible[1]
if #eligible > 1 and strategy == "shuffle" then
    local hash = 0
    for i = 1, #request_id do
        hash = (hash * 31 + string.byte(request_id, i)) % 2147483647
    end
    selected = eligible[(hash % #eligible) + 1]
elseif #eligible > 1 and strategy == "least_busy" then
    for i = 2, #eligible do
        local candidate = eligible[i]
        local candidate_is_better
        if any_uncapped then
            candidate_is_better = candidate.load < selected.load
        else
            candidate_is_better = (candidate.qos_limit - candidate.load) > (selected.qos_limit - selected.load)
        end

        local tied
        if any_uncapped then
            tied = candidate.load == selected.load
        else
            tied = (candidate.qos_limit - candidate.load) == (selected.qos_limit - selected.load)
        end

        if candidate_is_better or (tied and candidate.provider_id < selected.provider_id) then
            selected = candidate
        end
    end
end

redis.call("ZADD", selected.key, now_ms + heartbeat_ttl_ms, request_id)
return {"ADMITTED", selected.provider_id, depth}
"""


class RedisProviderQoS(ProviderQoS):
    LOAD_KEY_PREFIX = "ogl_qos:load"
    HEARTBEAT_INTERVAL_SECONDS = 10.0
    HEARTBEAT_TTL_MILLISECONDS = 30_000
    HEARTBEAT_RETRIES = 3
    HEARTBEAT_RETRY_BASE_SECONDS = 0.1

    def __init__(self, redis_client: AsyncRedis):
        self.redis_client = redis_client
        self._try_admit = redis_client.register_script(TRY_ADMIT_SCRIPT)

    @classmethod
    def _load_key(cls, provider_id: int) -> str:
        return f"{cls.LOAD_KEY_PREFIX}:{provider_id}"

    @staticmethod
    def _milliseconds(redis_time: tuple[int, int]) -> int:
        seconds, microseconds = redis_time
        return seconds * 1000 + microseconds // 1000

    async def _heartbeat(self, provider_id: int, request_id: str) -> None:
        key = self._load_key(provider_id)
        while True:
            await asyncio.sleep(self.HEARTBEAT_INTERVAL_SECONDS)

            for attempt in range(self.HEARTBEAT_RETRIES):
                try:
                    now_ms = self._milliseconds(await self.redis_client.time())
                    await self.redis_client.zadd(
                        key,
                        {request_id: now_ms + self.HEARTBEAT_TTL_MILLISECONDS},
                        xx=True,
                    )
                    break
                except RedisError:
                    if attempt < self.HEARTBEAT_RETRIES - 1:
                        await asyncio.sleep(self.HEARTBEAT_RETRY_BASE_SECONDS * (2**attempt))
            else:
                logger.error(
                    "Provider QoS heartbeat failed after %s attempts for request %s.",
                    self.HEARTBEAT_RETRIES,
                    request_id,
                )
                try:
                    await self.redis_client.zrem(key, request_id)
                except RedisError:
                    logger.exception("Failed to remove request %s after its QoS heartbeat failed.", request_id)
                return

    async def _release(self, provider_id: int, request_id: str) -> None:
        try:
            await self.redis_client.zrem(self._load_key(provider_id), request_id)
        except RedisError:
            logger.exception("Failed to release provider QoS reservation for request %s.", request_id)

    @asynccontextmanager
    async def admit(
        self,
        request_id: str,
        providers: list[Provider],
        strategy: RouterLoadBalancingStrategy,
        enforce_limit: bool,
    ):
        keys = [self._load_key(provider.id) for provider in providers]
        args: list[str | int] = [
            request_id,
            strategy.value,
            int(enforce_limit),
            self.HEARTBEAT_TTL_MILLISECONDS,
        ]
        for provider in providers:
            args.extend([provider.id, "none" if provider.qos_limit is None else provider.qos_limit])

        raw_result = await self._try_admit(keys=keys, args=args, client=self.redis_client)
        status = raw_result[0].decode() if isinstance(raw_result[0], bytes) else raw_result[0]
        if status == "FULL":
            yield ProviderAdmissionFull(depth=int(raw_result[2]))
            return

        selected_provider_id = int(raw_result[1])
        provider = next(provider for provider in providers if provider.id == selected_provider_id)
        heartbeat = asyncio.create_task(
            self._heartbeat(provider_id=provider.id, request_id=request_id),
            name=f"qos-heartbeat-{request_id}",
        )
        try:
            yield provider
        finally:
            heartbeat.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat
            await self._release(provider_id=provider.id, request_id=request_id)

    async def get_loads(self, provider_ids: list[int]) -> dict[int, int]:
        if not provider_ids:
            return {}

        now_ms = self._milliseconds(await self.redis_client.time())
        pipeline = self.redis_client.pipeline(transaction=True)
        for provider_id in provider_ids:
            key = self._load_key(provider_id)
            pipeline.zremrangebyscore(key, "-inf", now_ms)
            pipeline.zcard(key)
        results = await pipeline.execute()
        return {provider_id: int(results[index * 2 + 1]) for index, provider_id in enumerate(provider_ids)}
