import logging
from typing import Any

from billiard.exceptions import SoftTimeLimitExceeded
from celery.exceptions import MaxRetriesExceededError, Retry

from api.schemas.admin.routers import RouterLoadBalancingStrategy
from api.schemas.core.metrics import Metric
from api.tasks import app, create_model_queue, get_redis_client
from api.utils.load_balancing import apply_sync_load_balancing
from api.utils.qos import apply_sync_qos_policy

logger = logging.getLogger(__name__)


@app.task(name="routing.apply", bind=True)
def apply_routing(
    self,
    candidates: list[tuple[int, Metric | None, float | None]],
    load_balancing_strategy: RouterLoadBalancingStrategy,
    load_balancing_metric: Metric,
    task_retry_countdown: int,
    task_max_retries: int,
) -> dict[str, Any]:
    """
    Apply load balancing and qos policy to the candidates.

    Args:

        candidates (list[tuple[int, Metric | None, float | None]]): The list of provider candidates, tuple of (provider_id, qos_metric, qos_limit) to choose from
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
        qos_metric, qos_limit = [(metric, value) for id, metric, value in candidates if id == provider_id][0]
        can_be_forwarded = apply_sync_qos_policy(provider_id=provider_id, qos_metric=qos_metric, qos_limit=qos_limit, redis_client=redis_client)

        if can_be_forwarded:
            return {"status_code": 200, "provider_id": provider_id}
        else:
            raise self.retry(
                countdown=task_retry_countdown, max_retries=task_max_retries, declare=[create_model_queue(self.request.delivery_info["routing_key"])]
            )

    except Retry:
        raise
    except MaxRetriesExceededError:
        logger.error(f"Task {self.request.id}: Max retries exceeded", exc_info=True)
        return {"status_code": 503, "body": {"detail": "Max retries exceeded"}}
    except SoftTimeLimitExceeded:
        logger.error(f"Task {self.request.id}: Soft time limit exceeded", exc_info=True)
        return {"status_code": 504, "body": {"detail": "Model invocation exceeded the soft time limit"}}
    except Exception as e:  # pragma: no cover - defensive
        logger.exception(f"Task {self.request.id}: An unexpected error occurred", exc_info=True)
        return {"status_code": 500, "body": {"detail": type(e).__name__}}
