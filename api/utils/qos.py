from redis import Redis
from redis.asyncio import Redis as AsyncRedis

from api.schemas.core.metrics import Metric
from api.utils.variables import PREFIX__REDIS_METRIC_GAUGE


def apply_sync_qos_policy(provider_id: int, qos_metric: Metric | None, qos_limit: float | None, redis_client: Redis) -> bool:
    can_be_forwarded = True

    if qos_metric is None or qos_limit is None:
        return can_be_forwarded

    if qos_metric == Metric.INFLIGHT:
        inflight_requests = redis_client.get(f"{PREFIX__REDIS_METRIC_GAUGE}:{Metric.INFLIGHT.value}:{provider_id}")
        if inflight_requests is not None:
            inflight_requests = int(inflight_requests)
            if inflight_requests > qos_limit:
                can_be_forwarded = False

    return can_be_forwarded


async def apply_async_qos_policy(provider_id: int, qos_metric: Metric | None, qos_limit: float | None, redis_client: AsyncRedis) -> bool:
    can_be_forwarded = True

    if qos_metric is None or qos_limit is None:
        return can_be_forwarded

    if qos_metric == Metric.INFLIGHT:
        inflight_requests = await redis_client.get(f"{PREFIX__REDIS_METRIC_GAUGE}:{Metric.INFLIGHT.value}:{provider_id}")
        if inflight_requests is not None:
            inflight_requests = int(inflight_requests)
            if inflight_requests > qos_limit:
                can_be_forwarded = False

    return can_be_forwarded
