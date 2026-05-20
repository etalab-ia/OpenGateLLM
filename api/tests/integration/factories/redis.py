import time

from api.domain.provider.entities import Metric
from api.infrastructure.redis import RedisProviderMetricsLogger
from api.utils.variables import METRICS__TIMESERIE_RETENTION_SECONDS


class MetricsRedisFactory:
    @classmethod
    async def set_inflight(cls, redis_client, provider_id: int, value: int = 1) -> str:
        key = f"{RedisProviderMetricsLogger.PREFIX_REDIS_METRIC_GAUGE}:inflight:{provider_id}"
        await redis_client.set(key, value)

        return key

    @classmethod
    async def set_metric(cls, redis_client, provider_id: int, metric: Metric, values: list[float]) -> str:
        now_ms = int(time.time() * 1000)
        key = f"{RedisProviderMetricsLogger.PREFIX_REDIS_METRIC_TIMESERIE}:{metric.value}:{provider_id}"
        try:
            await redis_client.ts().create(key, retention_msecs=METRICS__TIMESERIE_RETENTION_SECONDS * 1000, duplicate_policy="LAST")
        except Exception:
            pass

        for i, value in enumerate(values):
            timestamp = now_ms - (len(values) - i) * 1000
            await redis_client.ts().add(key=key, timestamp=timestamp, value=value)

        return key
