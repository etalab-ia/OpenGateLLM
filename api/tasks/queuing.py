import logging
from typing import Any

from billiard.exceptions import SoftTimeLimitExceeded
from celery.exceptions import MaxRetriesExceededError, Retry

from api.schemas.admin.routers import RouterLoadBalancingStrategy as RouterLoadBalancingStrategyName
from api.schemas.core.metrics import MetricType
from api.tasks.celery_app import celery_app, get_redis_client
from api.utils.load_balancing import apply_sync_load_balancing
from api.utils.qos import apply_sync_qos_policy

logger = logging.getLogger(__name__)


# TODO ajouter tous les paramètres celery ?
@celery_app.task(name="model.invoke", bind=True)
def apply_load_balancing_with_queuing(
    self,
    candidates: list[tuple[int, MetricType | None, float | None]],
    load_balancing_strategy_name: RouterLoadBalancingStrategyName,
    load_balancing_metric: MetricType,
    task_retry_countdown: int,
    task_max_retries: int,
) -> dict[str, Any]:
    """Apply load balancing and qos policy to the candidates.

    Args:
        candidates (list[tuple[int, MetricType | None, float | None]]): The list of provider candidates, tuple of (provider_id, qos_metric, qos_threshold) to choose from
        load_balancing_strategy (RouterLoadBalancingStrategyName): The load balancing strategy to use
        load_balancing_metric (MetricType): The metric type to use for performance evaluation
        task_retry_countdown (int): The countdown to wait before retrying the task
        task_max_retries (int): The maximum number of retries

    Returns:
        dict[str, Any]: A dictionary containing the status code and the provider ID
    """
    try:
        redis_client = get_redis_client()

        provider_id, performance_indicator = apply_sync_load_balancing(
            load_balancing_strategy_name=load_balancing_strategy_name,
            candidates=[provider_id for provider_id, _, _ in candidates],
            redis_client=redis_client,
            load_balancing_metric=load_balancing_metric,
        )
        qos_metric, qos_threshold = [(metric, threshold) for candidate_id, metric, threshold in candidates if candidate_id == provider_id][0]
        can_be_forwarded = apply_sync_qos_policy(
            provider_id=provider_id,
            qos_metric=qos_metric,
            qos_threshold=qos_threshold,
            performance_indicator=performance_indicator,
            redis_client=redis_client,
        )
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


@celery_app.task(name="add.consumer")
def add_consumer(queue_name: str):
    celery_app.control.add_consumer(queue_name)


@celery_app.task(name="delete.consumer")
def delete_consumer(queue_name: str):
    celery_app.control.cancel_consumer(queue_name)
