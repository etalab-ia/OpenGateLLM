import logging
from typing import Any

from billiard.exceptions import SoftTimeLimitExceeded
from celery.exceptions import MaxRetriesExceededError, Retry
from redis.asyncio import Redis as AsyncRedis

from api.schemas.admin.routers import RouterLoadBalancingStrategy
from api.schemas.core.metrics import Metric
from api.tasks.celery_app import celery_app, get_redis_client
from api.utils.exceptions import ModelIsTooBusyException
from api.utils.load_balancing import apply_async_load_balancing, apply_sync_load_balancing
from api.utils.qos import apply_async_qos_policy, apply_sync_qos_policy

logger = logging.getLogger(__name__)


async def apply_load_balancing_and_qos_policy_without_queuing(
    candidates: list[tuple[int, Metric | None, float | None]],
    load_balancing_strategy: RouterLoadBalancingStrategy,
    load_balancing_metric: Metric,
    redis_client: AsyncRedis,
) -> tuple[int, float | None]:
    provider_id, _ = await apply_async_load_balancing(
        candidates=[provider_id for provider_id, _, _ in candidates],
        load_balancing_strategy=load_balancing_strategy,
        load_balancing_metric=load_balancing_metric,
        redis_client=redis_client,
    )
    qos_metric, qos_value = [(metric, value) for id, metric, value in candidates if id == provider_id][0]

    can_be_forwarded = await apply_async_qos_policy(
        provider_id=provider_id,
        qos_metric=qos_metric,
        qos_value=qos_value,
        redis_client=redis_client,
    )
    if not can_be_forwarded:
        raise ModelIsTooBusyException()

    return provider_id


@celery_app.task(name="model.invoke", bind=True)
def apply_load_balancing_and_qos_policy_with_queuing(
    self,
    candidates: list[tuple[int, Metric | None, float | None]],
    load_balancing_strategy: RouterLoadBalancingStrategy,
    load_balancing_metric: Metric,
    task_retry_countdown: int,
    task_max_retries: int,
) -> dict[str, Any]:
    """Apply load balancing and qos policy to the candidates.

    Args:
        candidates (list[tuple[int, Metric | None, float | None]]): The list of provider candidates, tuple of (provider_id, qos_metric, qos_value) to choose from
        load_balancing_strategy (RouterLoadBalancingStrategy): The load balancing strategy to use
        load_balancing_metric (Metric): The metric type to use for performance evaluation
        task_retry_countdown (int): The countdown to wait before retrying the task
        task_max_retries (int): The maximum number of retries

    Returns:
        dict[str, Any]: A dictionary containing the status code and the provider ID
    """
    try:
        redis_client = get_redis_client()

        provider_id, _ = apply_sync_load_balancing(
            load_balancing_strategy=load_balancing_strategy,
            candidates=[provider_id for provider_id, _, _ in candidates],
            redis_client=redis_client,
            load_balancing_metric=load_balancing_metric,
        )
        qos_metric, qos_value = [(metric, value) for id, metric, value in candidates if id == provider_id][0]
        can_be_forwarded = apply_sync_qos_policy(provider_id=provider_id, qos_metric=qos_metric, qos_value=qos_value, redis_client=redis_client)
        if can_be_forwarded:
            return {"status_code": 200, "provider_id": provider_id}
        else:
            raise self.retry(countdown=task_retry_countdown, max_retries=task_max_retries)

    except Retry:
        raise
    except MaxRetriesExceededError:
        return {"status_code": 503, "body": {"detail": "Max retries exceeded"}}
    except SoftTimeLimitExceeded:
        return {"status_code": 504, "body": {"detail": "Model invocation exceeded the soft time limit"}}
    except Exception as e:  # pragma: no cover - defensive
        return {"status_code": 500, "body": {"detail": type(e).__name__}}
