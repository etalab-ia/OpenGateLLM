import logging
import time

from redis.asyncio import Redis as AsyncRedis

from api.domain.model.entities import Metric
from api.infrastructure.fastapi.context import FastApiRequestManager
from api.utils.redis import redis_retry, safe_redis_reset
from api.utils.variables import PREFIX__REDIS_METRIC_GAUGE, PREFIX__REDIS_METRIC_TIMESERIE, REDIS__TIMESERIE_RETENTION_SECONDS

logger = logging.getLogger(__name__)


class ModelMetricsLogger:
    def __init__(self, request_manager: FastApiRequestManager):
        self.request_manager = request_manager

    async def log_performance(self, redis_client: AsyncRedis, provider_id: int, ttft: int | None, latency: int | None) -> None:
        self.request_manager.set_ttft(ttft)
        self.request_manager.set_latency(latency)

        try:
            if ttft is not None:
                key = f"{PREFIX__REDIS_METRIC_TIMESERIE}:{Metric.TTFT.value}:{provider_id}"
                await self._ensure_timeseries_exists(redis_client, key)
                await redis_client.ts().add(key=key, timestamp=int(time.time() * 1000), value=ttft)
        except Exception:
            logger.error(f"Failed to log request metrics (TTFT) in redis (id: {provider_id})", exc_info=True)
            await safe_redis_reset(redis_client)

        try:
            if latency is not None:
                key = f"{PREFIX__REDIS_METRIC_TIMESERIE}:{Metric.LATENCY.value}:{provider_id}"
                await self._ensure_timeseries_exists(redis_client, key)
                await redis_client.ts().add(key=key, timestamp=int(time.time() * 1000), value=latency)
        except Exception:
            logger.error(f"Failed to log request metrics (latency) in redis (id: {provider_id})", exc_info=True)
            await safe_redis_reset(redis_client)

    async def increment_inflight(self, redis_client: AsyncRedis, provider_id: int) -> bool:
        inflight_key = f"{PREFIX__REDIS_METRIC_GAUGE}:{Metric.INFLIGHT.value}:{provider_id}"
        try:
            await redis_retry(redis_client.incr, name=inflight_key, max_retries=2)
            return True
        except Exception:
            return False

    async def decrement_inflight(self, redis_client: AsyncRedis, provider_id: int, inflight_is_incremented: bool) -> None:
        if not inflight_is_incremented:
            return
        inflight_key = f"{PREFIX__REDIS_METRIC_GAUGE}:{Metric.INFLIGHT.value}:{provider_id}"
        try:
            await redis_retry(redis_client.decr, name=inflight_key, max_retries=2)
        except Exception as e:
            logger.exception(msg=f"Failed to decrement inflight key {inflight_key} for provider {provider_id}: {e}")

    @staticmethod
    async def _ensure_timeseries_exists(redis_client: AsyncRedis, key: str) -> None:
        try:
            await redis_client.ts().info(key)
        except Exception:
            try:
                await redis_client.ts().create(key, retention_msecs=REDIS__TIMESERIE_RETENTION_SECONDS * 1000, duplicate_policy="LAST")
            except Exception:
                pass
