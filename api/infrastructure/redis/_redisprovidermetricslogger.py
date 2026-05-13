import logging
import time

from redis.asyncio import Redis as AsyncRedis

from api.domain.provider import ProviderMetricsLogger
from api.domain.provider.entities import Metric
from api.utils.redis import redis_retry, safe_redis_reset
from api.utils.variables import METRICS__TIMESERIE_RETENTION_SECONDS, PREFIX__REDIS_METRIC_GAUGE, PREFIX__REDIS_METRIC_TIMESERIE

logger = logging.getLogger(__name__)


class RedisProviderMetricsLogger(ProviderMetricsLogger):
    def __init__(self, redis_client: AsyncRedis):
        self.redis_client = redis_client

    async def log_performance(self, provider_id: int | None, ttft: int | None, latency: int, completion_tokens: int) -> None:
        try:
            if ttft is not None:
                key = f"{PREFIX__REDIS_METRIC_TIMESERIE}:{Metric.TTFT.value}:{provider_id}"
                await self._ensure_timeseries_exists(key)
                await self.redis_client.ts().add(key=key, timestamp=int(time.time() * 1000), value=ttft)
        except Exception:
            logger.error(f"Failed to log request metrics (TTFT) in redis (id: {provider_id})", exc_info=True)
            await safe_redis_reset(self.redis_client)

        try:
            key = f"{PREFIX__REDIS_METRIC_TIMESERIE}:{Metric.LATENCY.value}:{provider_id}"
            await self._ensure_timeseries_exists(key)
            await self.redis_client.ts().add(key=key, timestamp=int(time.time() * 1000), value=latency)
        except Exception:
            logger.error(f"Failed to log request metrics (latency) in redis (id: {provider_id})", exc_info=True)
            await safe_redis_reset(self.redis_client)

        if completion_tokens > 0:
            try:
                key = f"{PREFIX__REDIS_METRIC_TIMESERIE}:{Metric.NORMALIZED_LATENCY.value}:{provider_id}"
                await self._ensure_timeseries_exists(key)
                await self.redis_client.ts().add(key=key, timestamp=int(time.time() * 1000), value=latency / completion_tokens)
            except Exception:
                logger.error(f"Failed to log request metrics (normalized latency) in redis (id: {provider_id})", exc_info=True)
                await safe_redis_reset(self.redis_client)

    async def increment_inflight(self, provider_id: int | None) -> bool:
        inflight_key = f"{PREFIX__REDIS_METRIC_GAUGE}:{Metric.INFLIGHT.value}:{provider_id}"
        try:
            await redis_retry(self.redis_client.incr, name=inflight_key, max_retries=2)
            return True
        except Exception:
            return False

    async def decrement_inflight(self, provider_id: int | None, inflight_is_incremented: bool) -> None:
        if not inflight_is_incremented:
            return
        inflight_key = f"{PREFIX__REDIS_METRIC_GAUGE}:{Metric.INFLIGHT.value}:{provider_id}"
        try:
            await redis_retry(self.redis_client.decr, name=inflight_key, max_retries=2)
        except Exception as e:
            logger.exception(msg=f"Failed to decrement inflight key {inflight_key} for provider {provider_id}: {e}")

    async def _ensure_timeseries_exists(self, key: str) -> None:
        try:
            await self.redis_client.ts().info(key)
        except Exception:
            try:
                await self.redis_client.ts().create(key, retention_msecs=METRICS__TIMESERIE_RETENTION_SECONDS * 1000, duplicate_policy="LAST")
            except Exception:
                pass

    async def get_historical_normalized_latencies(self, provider_id: int, from_time: int | None = None) -> list[float]:
        key = f"{PREFIX__REDIS_METRIC_TIMESERIE}:{Metric.NORMALIZED_LATENCY.value}:{provider_id}"
        if not await self.redis_client.exists(key):
            return []

        to_time = int(time.time() * 1000)
        if from_time is None:
            from_time = to_time - METRICS__TIMESERIE_RETENTION_SECONDS * 1000
        values = await self.redis_client.ts().range(key=key, from_time=from_time, to_time=to_time)
        values = [latency for _, latency in values]

        return values

    async def get_current_inflight(self, provider_id: int) -> int:
        key = f"{PREFIX__REDIS_METRIC_GAUGE}:{Metric.INFLIGHT.value}:{provider_id}"
        if not await self.redis_client.exists(key):
            return 0

        value = await self.redis_client.get(key)
        return int(value) if value is not None else 0
