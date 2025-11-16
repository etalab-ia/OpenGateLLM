import logging
from typing import Any

from billiard.exceptions import SoftTimeLimitExceeded
from celery.exceptions import MaxRetriesExceededError, Retry

from api.schemas.admin.routers import RouterLoadBalancingStrategy
from api.schemas.core.metrics import Metric
from api.tasks.celery_app import celery_app, get_redis_client
from api.utils.load_balancing import apply_sync_load_balancing
from api.utils.qos import apply_sync_qos_policy

logger = logging.getLogger(__name__)


@celery_app.task(name="model.invoke", bind=True)
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
    logger.info(f"Task {self.request.id} started: candidates={len(candidates)}, strategy={load_balancing_strategy}, metric={load_balancing_metric}")
    try:
        logger.debug(f"Task {self.request.id}: Getting Redis client")
        redis_client = get_redis_client()

        logger.debug(f"Task {self.request.id}: Applying load balancing")
        provider_id, _ = apply_sync_load_balancing(
            load_balancing_strategy=load_balancing_strategy,
            candidates=[provider_id for provider_id, _, _ in candidates],
            redis_client=redis_client,
            load_balancing_metric=load_balancing_metric,
        )
        logger.info(f"Task {self.request.id}: Selected provider_id={provider_id}")

        qos_metric, qos_limit = [(metric, value) for id, metric, value in candidates if id == provider_id][0]
        logger.debug(f"Task {self.request.id}: Applying QoS policy (metric={qos_metric}, limit={qos_limit})")
        can_be_forwarded = apply_sync_qos_policy(provider_id=provider_id, qos_metric=qos_metric, qos_limit=qos_limit, redis_client=redis_client)

        if can_be_forwarded:
            logger.info(f"Task {self.request.id}: Successfully completed, returning provider_id={provider_id}")
            return {"status_code": 200, "provider_id": provider_id}
        else:
            logger.warning(
                f"Task {self.request.id}: Provider {provider_id} cannot be forwarded, retrying (attempt {self.request.retries + 1}/{task_max_retries})"
            )
            raise self.retry(countdown=task_retry_countdown, max_retries=task_max_retries)

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
