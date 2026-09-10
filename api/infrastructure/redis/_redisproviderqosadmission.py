import asyncio
import logging
import random
import time

from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import ConnectionError, RedisError, TimeoutError

from api.domain.provider._providerqosadmission import (
    ProviderQosAdmission,
    QosAdmissionFull,
    QosAdmissionGranted,
    QosAdmissionResult,
)
from api.domain.provider.entities import Provider
from api.domain.router.entities import RouterLoadBalancingStrategy
from api.utils.variables import (
    PREFIX__REDIS_QOS_LOAD,
    QOS_HEARTBEAT_INTERVAL_SECONDS,
    QOS_HEARTBEAT_REDIS_RETRIES,
    QOS_HEARTBEAT_TTL_MS,
)

logger = logging.getLogger(__name__)

_TRY_ADMIT_LUA = """
local request_id = ARGV[1]
local strategy = ARGV[2]
local n = tonumber(ARGV[3])
local shuffle_index = tonumber(ARGV[4])
local heartbeat_ttl_ms = tonumber(ARGV[5])

local time = redis.call('TIME')
local now_ms = tonumber(time[1]) * 1000 + math.floor(tonumber(time[2]) / 1000)

local providers = {}
local loads = {}
local depth = 0

for i = 1, n do
  local provider_id = ARGV[5 + (i - 1) * 2 + 1]
  local limit_raw = ARGV[5 + (i - 1) * 2 + 2]
  local limit = nil
  if limit_raw ~= '' then
    limit = tonumber(limit_raw)
  end
  providers[i] = {id = provider_id, limit = limit, key = KEYS[i]}
  redis.call('ZREMRANGEBYSCORE', KEYS[i], '-inf', now_ms)
  loads[i] = redis.call('ZCARD', KEYS[i])
  depth = depth + loads[i]
end

local eligible = {}
for i = 1, n do
  local limit = providers[i].limit
  if limit == nil then
    table.insert(eligible, i)
  elseif limit > 0 and loads[i] < limit then
    table.insert(eligible, i)
  end
end

if #eligible == 0 then
  return {'FULL', tostring(depth)}
end

local chosen = eligible[1]
if #eligible > 1 then
  if strategy == 'shuffle' then
    chosen = eligible[((shuffle_index - 1) % #eligible) + 1]
  else
    local has_unlimited = false
    for _, idx in ipairs(eligible) do
      if providers[idx].limit == nil then
        has_unlimited = true
        break
      end
    end
    for j = 2, #eligible do
      local idx = eligible[j]
      if has_unlimited then
        if loads[idx] < loads[chosen]
          or (loads[idx] == loads[chosen] and tonumber(providers[idx].id) < tonumber(providers[chosen].id)) then
          chosen = idx
        end
      else
        local remaining = providers[idx].limit - loads[idx]
        local chosen_remaining = providers[chosen].limit - loads[chosen]
        if remaining > chosen_remaining
          or (remaining == chosen_remaining and tonumber(providers[idx].id) < tonumber(providers[chosen].id)) then
          chosen = idx
        end
      end
    end
  end
end

redis.call('ZADD', providers[chosen].key, now_ms + heartbeat_ttl_ms, request_id)
return {'ADMITTED', providers[chosen].id}
"""


class RedisProviderQosAdmission(ProviderQosAdmission):
    def __init__(self, redis_client: AsyncRedis):
        self.redis_client = redis_client
        self._try_admit = self.redis_client.register_script(_TRY_ADMIT_LUA)
        self._heartbeat_tasks: dict[tuple[int, str], asyncio.Task] = {}

    @staticmethod
    def _load_key(provider_id: int) -> str:
        return f"{PREFIX__REDIS_QOS_LOAD}:{provider_id}"

    @staticmethod
    def _serialize_qos_limit(qos_limit: float | None) -> str:
        if qos_limit is None:
            return ""
        return str(int(qos_limit))

    async def try_admit(
        self,
        providers: list[Provider],
        strategy: RouterLoadBalancingStrategy,
        request_id: str,
    ) -> QosAdmissionResult:
        if not providers:
            return QosAdmissionFull(depth=0)

        keys = [self._load_key(provider.id) for provider in providers]
        args = [
            request_id,
            strategy.value,
            str(len(providers)),
            str(random.randint(1, max(len(providers) * 1000, 1))),
            str(QOS_HEARTBEAT_TTL_MS),
        ]
        for provider in providers:
            args.append(str(provider.id))
            args.append(self._serialize_qos_limit(provider.qos_limit))

        result = await self._try_admit(keys=keys, args=args)
        status = result[0].decode() if isinstance(result[0], bytes) else result[0]
        value = result[1].decode() if isinstance(result[1], bytes) else result[1]

        if status == "ADMITTED":
            return QosAdmissionGranted(provider_id=int(value))
        return QosAdmissionFull(depth=int(value))

    async def start_heartbeat(self, provider_id: int, request_id: str) -> None:
        key = (provider_id, request_id)
        if key in self._heartbeat_tasks:
            return
        self._heartbeat_tasks[key] = asyncio.create_task(
            self._heartbeat_loop(provider_id=provider_id, request_id=request_id),
            name=f"qos-heartbeat-{provider_id}-{request_id}",
        )

    async def release(self, provider_id: int, request_id: str) -> None:
        task_key = (provider_id, request_id)
        task = self._heartbeat_tasks.pop(task_key, None)
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        try:
            await self.redis_client.zrem(self._load_key(provider_id), request_id)
        except Exception:
            logger.exception("Failed to release QoS load member", extra={"provider_id": provider_id, "request_id": request_id})

    async def _heartbeat_loop(self, provider_id: int, request_id: str) -> None:
        key = self._load_key(provider_id)
        try:
            while True:
                await asyncio.sleep(QOS_HEARTBEAT_INTERVAL_SECONDS)
                refreshed = await self._refresh_heartbeat(key=key, request_id=request_id)
                if not refreshed:
                    return
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("QoS heartbeat loop failed", extra={"provider_id": provider_id, "request_id": request_id})

    async def _refresh_heartbeat(self, key: str, request_id: str) -> bool:
        for attempt in range(QOS_HEARTBEAT_REDIS_RETRIES):
            try:
                score = int(time.time() * 1000) + QOS_HEARTBEAT_TTL_MS
                updated = await self.redis_client.zadd(key, {request_id: score}, xx=True)
                return bool(updated)
            except (ConnectionError, TimeoutError, RedisError) as exc:
                if attempt < QOS_HEARTBEAT_REDIS_RETRIES - 1:
                    logger.warning(
                        "QoS heartbeat Redis write failed (attempt %s/%s): %s",
                        attempt + 1,
                        QOS_HEARTBEAT_REDIS_RETRIES,
                        exc,
                    )
                    await asyncio.sleep(0.1 * (2**attempt))
                else:
                    logger.error(
                        "QoS heartbeat Redis write failed after %s attempts; releasing load member",
                        QOS_HEARTBEAT_REDIS_RETRIES,
                        exc_info=True,
                    )
                    try:
                        await self.redis_client.zrem(key, request_id)
                    except Exception:
                        logger.exception("Failed to ZREM after heartbeat failure", extra={"key": key, "request_id": request_id})
                    return False
        return False
