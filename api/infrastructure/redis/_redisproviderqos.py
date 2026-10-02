import asyncio
from contextlib import asynccontextmanager, suppress
import logging

from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import RedisError

from api.domain.provider._providerqos import ProviderAdmissionFull, ProviderQoS
from api.domain.provider.entities import Provider
from api.domain.router.entities import RouterLoadBalancingStrategy

logger = logging.getLogger(__name__)

# Picks a provider for one request and reserves a place on it.
#
# Each provider has a sorted set in Redis. It holds one entry per request in progress,
# and the entry's score is the time (in ms) after which it counts as abandoned.
# The number of entries is the provider's current load.
#
# Redis runs the whole script without interruption: no other request can read or change
# a load between the moment it is counted and the moment the reservation is written.
# That is what prevents two requests from taking the last free place together.
#
# Inputs, in the order built by RedisProviderQoS.admit:
#   KEYS[i]    sorted set of the i-th provider
#   ARGV[1]    request id, written as the reservation entry
#   ARGV[2]    "shuffle" or "least_busy"
#   ARGV[3]    "1": a provider at its limit is refused. "0": the limit is ignored.
#   ARGV[4]    lifetime of a reservation in ms, renewed by the heartbeat
#   then two values per provider, in the same order as KEYS:
#              its id, and its limit ("none" when it has no limit)
#
# Result: {"ADMITTED", chosen provider id, total load}
#      or {"FULL", 0, total load} when no provider can take the request.
TRY_ADMIT_SCRIPT = """
local request_id = ARGV[1]
local strategy = ARGV[2]
local enforce_limit = ARGV[3] == "1"
local reservation_ms = tonumber(ARGV[4])
local FIRST_PROVIDER_ARG = 5

local time = redis.call("TIME")
local now_ms = time[1] * 1000 + math.floor(time[2] / 1000)

-- 1. Read every provider and keep those that can take the request.
local candidates = {}
local total_load = 0
local some_candidate_has_no_limit = false

for i, key in ipairs(KEYS) do
    local arg = FIRST_PROVIDER_ARG + (i - 1) * 2
    local provider_id = tonumber(ARGV[arg])
    local limit = nil
    if ARGV[arg + 1] ~= "none" then
        limit = tonumber(ARGV[arg + 1])
    end

    -- Drop reservations whose worker stopped without releasing them, then count the rest.
    redis.call("ZREMRANGEBYSCORE", key, "-inf", now_ms)
    local load = redis.call("ZCARD", key)
    total_load = total_load + load

    local accepts
    if limit == nil then
        accepts = true
    elseif limit == 0 then
        accepts = false -- a limit of 0 means the provider is closed
    else
        accepts = not enforce_limit or load < limit
    end

    if accepts then
        table.insert(candidates, {key = key, provider_id = provider_id, limit = limit, load = load})
        if limit == nil then
            some_candidate_has_no_limit = true
        end
    end
end

if #candidates == 0 then
    return {"FULL", 0, total_load}
end

-- 2. Choose one candidate.
local chosen = candidates[1]

-- Nothing to choose when a single provider can take the request.
if #candidates == 1 then
    redis.call("ZADD", chosen.key, now_ms + reservation_ms, request_id)
    return {"ADMITTED", chosen.provider_id, total_load}
end

if strategy == "shuffle" then
    -- Scripts cannot draw a random number that differs between calls, so the request id
    -- is turned into a number and used to pick a candidate. Different ids spread evenly.
    local number = 0
    for i = 1, #request_id do
        number = (number * 31 + string.byte(request_id, i)) % 2147483647
    end
    chosen = candidates[(number % #candidates) + 1]

elseif strategy == "least_busy" then
    -- Higher is better. Free places cannot be compared when a provider has no limit,
    -- so in that case the provider with the fewest requests in progress wins.
    local function availability(candidate)
        if some_candidate_has_no_limit then
            return -candidate.load
        end
        return candidate.limit - candidate.load
    end

    for i = 2, #candidates do
        local candidate = candidates[i]
        local difference = availability(candidate) - availability(chosen)
        -- On equal availability, the smallest id wins, so the choice is predictable.
        if difference > 0 or (difference == 0 and candidate.provider_id < chosen.provider_id) then
            chosen = candidate
        end
    end
end

-- 3. Reserve a place on the chosen provider.
redis.call("ZADD", chosen.key, now_ms + reservation_ms, request_id)
return {"ADMITTED", chosen.provider_id, total_load}
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
                    await self.redis_client.zadd(key, {request_id: now_ms + self.HEARTBEAT_TTL_MILLISECONDS}, xx=True)
                    break
                except RedisError:
                    if attempt < self.HEARTBEAT_RETRIES - 1:
                        await asyncio.sleep(self.HEARTBEAT_RETRY_BASE_SECONDS * (2**attempt))
            else:
                logger.error("Provider QoS heartbeat failed after %s attempts for request %s.", self.HEARTBEAT_RETRIES, request_id)
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
        # Layout documented above TRY_ADMIT_SCRIPT: four fixed values, then (id, limit) per provider.
        keys = [self._load_key(provider.id) for provider in providers]
        args = [request_id, strategy.value, int(enforce_limit), self.HEARTBEAT_TTL_MILLISECONDS]
        for provider in providers:
            # Redis arguments are strings and cannot be empty, so "no limit" is sent as "none".
            args.extend([provider.id, "none" if provider.qos_limit is None else provider.qos_limit])

        raw_result = await self._try_admit(keys=keys, args=args, client=self.redis_client)
        status = raw_result[0].decode() if isinstance(raw_result[0], bytes) else raw_result[0]
        if status == "FULL":
            yield ProviderAdmissionFull(depth=int(raw_result[2]))
            return

        selected_provider_id = int(raw_result[1])
        provider = next(provider for provider in providers if provider.id == selected_provider_id)
        # create_task schedules the refresh loop immediately. yield then suspends this
        # context until the caller leaves the async with, so the task runs for the
        # whole provider call and is cancelled in the finally below.
        heartbeat = asyncio.create_task(self._heartbeat(provider_id=provider.id, request_id=request_id), name=f"qos-heartbeat-{request_id}")
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
