from redis import Redis
from redis.asyncio import Redis as AsyncRedis

from api.schemas.core.metrics import MetricType
from api.utils.variables import METRIC__GAUGE_PREFIX


def apply_sync_qos_policy(
    provider_id: int, qos_metric: MetricType | None, qos_limit: float | None, performance_indicator: float | None, redis_client: Redis
) -> bool:
    can_be_forwarded = True
    if qos_metric is not None and qos_metric == MetricType.INFLIGHT:
        inflight_requests = redis_client.get(f"{METRIC__GAUGE_PREFIX}:{MetricType.INFLIGHT.value}:{provider_id}")
        if inflight_requests is not None and qos_limit is not None:
            inflight_requests = int(inflight_requests)
            if inflight_requests > qos_limit:
                can_be_forwarded = False

    return can_be_forwarded


async def apply_async_qos_policy(
    provider_id: int, qos_metric: MetricType | None, qos_limit: float | None, performance_indicator: float | None, redis_client: AsyncRedis
) -> bool:
    can_be_forwarded = True
    if qos_metric is not None and qos_metric == MetricType.INFLIGHT:
        inflight_requests = await redis_client.get(f"{METRIC__GAUGE_PREFIX}:{MetricType.INFLIGHT.value}:{provider_id}")
        if inflight_requests is not None and qos_limit is not None:
            inflight_requests = int(inflight_requests)
            if inflight_requests > qos_limit:
                can_be_forwarded = False

    return can_be_forwarded
