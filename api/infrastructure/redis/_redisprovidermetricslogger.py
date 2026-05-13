import logging
import time

from redis.asyncio import Redis as AsyncRedis

from api.domain.model.entities import Metric
from api.domain.provider import ProviderMetricsLogger
from api.utils.redis import redis_retry, safe_redis_reset
from api.utils.variables import PREFIX__REDIS_METRIC_GAUGE, PREFIX__REDIS_METRIC_TIMESERIE, REDIS__TIMESERIE_RETENTION_SECONDS

logger = logging.getLogger(__name__)


class RedisProviderMetricsLogger(ProviderMetricsLogger):
    def __init__(self, redis_client: AsyncRedis):
        self.redis_client = redis_client

    async def log_performance(self, provider_id: int | None, ttft: int | None, latency: int | None) -> None:
        try:
            if ttft is not None:
                key = f"{PREFIX__REDIS_METRIC_TIMESERIE}:{Metric.TTFT.value}:{provider_id}"
                await self._ensure_timeseries_exists(key)
                await self.redis_client.ts().add(key=key, timestamp=int(time.time() * 1000), value=ttft)
        except Exception:
            logger.error(f"Failed to log request metrics (TTFT) in redis (id: {provider_id})", exc_info=True)
            await safe_redis_reset(self.redis_client)

        try:
            if latency is not None:
                key = f"{PREFIX__REDIS_METRIC_TIMESERIE}:{Metric.LATENCY.value}:{provider_id}"
                await self._ensure_timeseries_exists(key)
                await self.redis_client.ts().add(key=key, timestamp=int(time.time() * 1000), value=latency)
        except Exception:
            logger.error(f"Failed to log request metrics (latency) in redis (id: {provider_id})", exc_info=True)
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
                await self.redis_client.ts().create(key, retention_msecs=REDIS__TIMESERIE_RETENTION_SECONDS * 1000, duplicate_policy="LAST")
            except Exception:
                pass
