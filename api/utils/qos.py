from redis import Redis
from redis.asyncio import Redis as AsyncRedis

from api.schemas.core.metrics import Metric
from api.utils.variables import METRIC__GAUGE_PREFIX


def apply_sync_qos_policy(provider_id: int, qos_metric: Metric, qos_value: float | None, redis_client: Redis) -> bool:
    can_be_forwarded = True

    if qos_value is None:
        return can_be_forwarded

    if qos_metric == Metric.INFLIGHT:
        inflight_requests = redis_client.get(f"{METRIC__GAUGE_PREFIX}:{Metric.INFLIGHT.value}:{provider_id}")
        if inflight_requests is not None:
            inflight_requests = int(inflight_requests)
            if inflight_requests > qos_value:
                can_be_forwarded = False

    return can_be_forwarded


async def apply_async_qos_policy(provider_id: int, qos_metric: Metric, qos_value: float | None, redis_client: AsyncRedis) -> bool:
    can_be_forwarded = True

    if qos_value is None:
        return can_be_forwarded

    if qos_metric == Metric.INFLIGHT:
        inflight_requests = await redis_client.get(f"{METRIC__GAUGE_PREFIX}:{Metric.INFLIGHT.value}:{provider_id}")
        if inflight_requests is not None:
            inflight_requests = int(inflight_requests)
            if inflight_requests > qos_value:
                can_be_forwarded = False

    return can_be_forwarded
