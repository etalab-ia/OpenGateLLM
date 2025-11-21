import asyncio
import logging

from celery.result import AsyncResult
from redis.asyncio import Redis as AsyncRedis

from api.schemas.admin.providers import Provider
from api.schemas.admin.routers import RouterLoadBalancingStrategy
from api.schemas.core.metrics import Metric
from api.tasks import app, create_model_queue
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

    while max_retries > 0:
        can_be_forwarded = await apply_async_qos_policy(
            provider_id=provider_id,
            qos_metric=qos_metric,
            qos_limit=qos_limit,
            redis_client=redis_client,
        )
        if can_be_forwarded:
            break
        await asyncio.sleep(retry_countdown)
        max_retries -= 1

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

    queue_obj = create_model_queue(queue_name)
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
        declare=[queue_obj],
    )

    async_result = AsyncResult(id=task.id, app=app)
    initial_state = async_result.state
    logger.info(f"Task {task.id} sent to queue '{queue_name}', initial state: {initial_state}, waiting for result...")

    loop = asyncio.get_event_loop()
    start_time = loop.time()

    task_interval = 0.1  # polling interval to check if the task is ready
    task_timeout = 0.2  # estimed task execution time
    max_wait_time = max_retries * (retry_countdown + task_timeout)
    logger.debug(f"Task {task.id}: Polling for result (max wait: {max_wait_time}s, interval: {task_interval}s)")

    poll_count = 0
    last_state = initial_state
    while not async_result.ready():
        elapsed = loop.time() - start_time
        current_state = async_result.state

        # Log state changes
        if current_state != last_state:
            logger.info(f"Task {task.id}: State changed from {last_state} to {current_state} (elapsed: {elapsed:.2f}s)")
            last_state = current_state

        if elapsed > max_wait_time:
            logger.error(f"Task {task.id}: Timeout after {elapsed:.2f}s (state: {current_state})")
            # Try to get more info about the task
            try:
                info = async_result.info
                logger.error(f"Task {task.id}: Info={info}")
            except Exception as e:
                logger.error(f"Task {task.id}: Could not get task info: {e}")
            raise ModelIsTooBusyException(detail=f"Model is too busy after {max_wait_time} seconds")

        poll_count += 1
        if poll_count % 10 == 0:  # Log every second (10 * 0.1s)
            logger.debug(f"Task {task.id}: Still waiting... (elapsed: {elapsed:.2f}s, state: {current_state})")

        await asyncio.sleep(task_interval)

    try:
        state = async_result.state
        logger.info(f"Task {task.id}: Completed with state={state}")
        result = async_result.result  # direct access is safe after ready() returns True
        logger.debug(f"Task {task.id}: Result={result}")

        if result["status_code"] != 200:
            logger.error(f"Task {task.id}: Failed with status_code={result["status_code"]}, detail={result.get("body", {}).get("detail", "N/A")}")
            raise TaskFailedException(status_code=result["status_code"], detail=result["body"]["detail"])
        provider_id = result["provider_id"]
        logger.info(f"Task {task.id}: Successfully returned provider_id={provider_id}")

    except TaskFailedException:
        raise
    except Exception as e:
        logger.error(f"Task {task.id}: Error retrieving result: {e}", exc_info=True)
        raise TaskFailedException(status_code=500, detail=str(e))

    return provider_id
