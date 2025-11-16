import asyncio
import logging

from celery.result import AsyncResult
from redis.asyncio import Redis as AsyncRedis

from api.schemas.admin.providers import Provider
from api.schemas.admin.routers import RouterLoadBalancingStrategy
from api.schemas.core.metrics import Metric
from api.tasks.celery_app import celery_app, ensure_queue_exists
from api.tasks.routing import apply_routing
from api.utils.exceptions import ModelIsTooBusyException, TaskFailedException
from api.utils.load_balancing import apply_async_load_balancing
from api.utils.qos import apply_async_qos_policy

logger = logging.getLogger(__name__)


async def apply_routing_without_queuing(
    providers: list[Provider],
    load_balancing_strategy: RouterLoadBalancingStrategy,
    load_balancing_metric: Metric,
    max_retries: int,
    retry_countdown: int,
    redis_client: AsyncRedis,
) -> int:
    if len(providers) == 1:
        provider_id = providers[0].id
    else:
        provider_id, _ = await apply_async_load_balancing(
            candidates=[provider.id for provider in providers],
            load_balancing_strategy=load_balancing_strategy,
            load_balancing_metric=load_balancing_metric,
            redis_client=redis_client,
        )

    qos_metric, qos_limit = [(provider.qos_metric, provider.qos_limit) for provider in providers if provider.id == provider_id][0]

    can_be_forwarded = False
    for _ in range(max_retries):
        can_be_forwarded = await apply_async_qos_policy(
            provider_id=provider_id,
            qos_metric=qos_metric,
            qos_limit=qos_limit,
            redis_client=redis_client,
        )
        if can_be_forwarded:
            break
        await asyncio.sleep(retry_countdown)

    if not can_be_forwarded:
        raise ModelIsTooBusyException(detail=f"Model is too busy after {max_retries * retry_countdown} seconds")

    return provider_id


async def apply_routing_with_queuing(
    providers: list[Provider],
    load_balancing_strategy: RouterLoadBalancingStrategy,
    load_balancing_metric: Metric,
    retry_countdown: int,
    max_retries: int,
    queue_name: str,
    priority: int,
) -> int:
    candidates = [(provider.id, provider.qos_metric, provider.qos_limit) for provider in providers]
    ensure_queue_exists(queue_name)

    task = apply_routing.apply_async(
        args=[
            candidates,  # candidates
            load_balancing_strategy,  # load_balancing_strategy
            load_balancing_metric,  # load_balancing_metric
            retry_countdown,  # task_retry_countdown
            max_retries,  # task_max_retries
        ],
        queue=queue_name,
        priority=priority,
    )

    async_result = AsyncResult(id=task.id, app=celery_app)
    loop = asyncio.get_event_loop()
    start_time = loop.time()

    task_interval = 0.1  # polling interval to check if the task is ready
    task_timeout = 0.2  # estimed task execution time
    while not async_result.ready():
        if loop.time() - start_time > max_retries * (retry_countdown + task_timeout):
            raise ModelIsTooBusyException(detail=f"Model is too busy after {max_retries * retry_countdown} seconds")
        await asyncio.sleep(task_interval)

    try:
        result = async_result.result  # direct access is safe after ready() returns True
        if result["status_code"] != 200:
            raise TaskFailedException(status_code=result["status_code"], detail=result["body"]["detail"])
        provider_id = result["provider_id"]

    except TaskFailedException:
        raise
    except Exception as e:
        logger.warning(f"Error retrieving result for task {task.id}: {e}")
        raise TaskFailedException(status_code=500, detail=str(e))

    return provider_id
