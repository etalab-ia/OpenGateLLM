import logging

from celery import Celery
from celery.signals import worker_init, worker_ready
from kombu import Queue
from redis import ConnectionPool, Redis

from api.utils.configuration import configuration

logger = logging.getLogger(__name__)

# Redis connection pool - initialized when worker starts
_redis_pool = None


@worker_init.connect
def init_redis_pool(**kwargs):
    """Initialize Redis connection pool when Celery worker starts."""
    global _redis_pool
    _redis_pool = ConnectionPool.from_url(url=configuration.dependencies.redis.url)
    logger.info("Redis connection pool initialized for Celery worker")

    # import tasks to ensure they are registered with Celery
    # from api.tasks import routing  # noqa: F401,E402


@worker_ready.connect
def auto_subscribe_to_task_queues(**kwargs):
    """
    Automatically subscribe worker to all queues defined in task_queues.
    This makes the system fully dynamic without requiring -Q option or add_consumer().
    """
    # The worker starts by listening only to the default 'celery' queue
    # We need to manually subscribe to all other queues in task_queues
    if celery_app.conf.task_queues:
        queue_names = [q.name for q in celery_app.conf.task_queues]
        logger.info(f"Worker ready. Auto-subscribing to queues from task_queues: {", ".join(queue_names)}")

        # Get the worker's consumer to add queues
        # We need to access the worker's consumer and add queues directly
        try:
            # Access the worker instance from kwargs
            worker = kwargs.get("sender")
            if worker and hasattr(worker, "consumer"):
                consumer = worker.consumer
                if hasattr(consumer, "add_task_queue"):
                    # Subscribe to all queues except 'celery' (already listening)
                    queues_to_add = [q for q in celery_app.conf.task_queues if q.name != "celery"]
                    for queue in queues_to_add:
                        try:
                            # Use the queue definition from task_queues which includes priority arguments
                            consumer.add_task_queue(queue)
                            logger.info(f"Worker subscribed to queue '{queue.name}' with priority arguments")
                        except Exception as e:
                            logger.warning(f"Failed to subscribe worker to queue '{queue.name}': {e}", exc_info=True)
                else:
                    logger.warning("Worker consumer does not have add_task_queue method")
            else:
                logger.debug("Could not access worker consumer, skipping auto-subscription")
        except Exception as e:
            logger.warning(f"Failed to auto-subscribe worker to task_queues: {e}", exc_info=True)
    else:
        logger.info("Worker ready. Listening to default queue: celery")


def get_redis_client() -> Redis:
    """
    Get a synchronous Redis client for use in Celery tasks.

    Returns:
        Redis: A synchronous Redis client instance.

    Raises:
        RuntimeError: If called before worker initialization.
    """
    if _redis_pool is None:
        raise RuntimeError("Redis pool not initialized. This function should only be called within Celery tasks after worker initialization.")
    return Redis.from_pool(connection_pool=_redis_pool)


celery_app = Celery(main=configuration.settings.app_title)

celery_app.conf.update(
    broker_url=configuration.dependencies.celery.broker_url,
    result_backend=configuration.dependencies.celery.result_backend,
    worker_prefetch_multiplier=configuration.dependencies.celery.worker_prefetch_multiplier,
    timezone=configuration.dependencies.celery.timezone,
    enable_utc=configuration.dependencies.celery.enable_utc,
    task_max_priority=configuration.settings.routing_max_priority,
    task_acks_late=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_create_missing_queues=False,
    task_default_queue="celery",
)


def ensure_queue_exists(queue_name: str) -> None:
    """
    Ensure a queue exists with proper configuration (priority support for RabbitMQ).
    This function declares the queue with priority arguments, even if it already exists.
    It also dynamically subscribes all active workers to this queue, making the system
    fully dynamic without requiring -Q option at worker startup.

    Args:
        queue_name: The name of the queue to ensure exists
    """
    if configuration.dependencies.celery is None:
        return

    # Create queue definition with priority arguments
    queue = Queue(queue_name, routing_key=queue_name, queue_arguments={"x-max-priority": configuration.settings.routing_max_priority + 1})

    # Add to task_queues configuration
    existing_queues = celery_app.conf.task_queues or ()
    queue_names = {q.name for q in existing_queues}
    if queue_name not in queue_names:
        celery_app.conf.task_queues = existing_queues + (queue,)

    # Dynamically subscribe all active workers to this queue
    inspect = celery_app.control.inspect()
    active_workers = inspect.active()
    if active_workers:
        worker_names = list(active_workers.keys())
        logger.info(f"Subscribing {len(worker_names)} active worker(s) to queue '{queue_name}'")
        celery_app.control.add_consumer(queue_name, destination=worker_names)


if configuration.dependencies.celery is not None:
    ensure_queue_exists("celery")


# # Override the default add_consumer command to use queue definitions from task_queues
# # This ensures that when add_consumer() is called, it uses the queue definition
# # from task_queues which includes priority arguments, avoiding PreconditionFailed errors
# def add_consumer_with_priority(state, queue=None, exchange=None, exchange_type="direct", routing_key=None, **options):
#     """
#     Custom add_consumer command that uses queue definition from task_queues.
#     This ensures that queues are declared with priority arguments.
#     """
#     if not queue:
#         return {"error": "queue name is required"}

#     # Find the queue definition in task_queues
#     queue_def = None
#     if celery_app.conf.task_queues:
#         for q in celery_app.conf.task_queues:
#             if q.name == queue:
#                 queue_def = q
#                 break

#     # If queue not found in task_queues, create it with priority arguments
#     if not queue_def:
#         logger.info(f"Queue '{queue}' not found in task_queues, creating with priority arguments")
#         # Create queue definition with priority arguments
#         queue_def = Queue(
#             queue,
#             routing_key=routing_key or queue,
#             exchange=exchange,
#             exchange_type=exchange_type or "direct",
#             queue_arguments={"x-max-priority": configuration.settings.routing_max_priority + 1},
#         )
#         # Add to task_queues for future reference
#         existing_queues = celery_app.conf.task_queues or ()
#         queue_names = {q.name for q in existing_queues}
#         if queue not in queue_names:
#             celery_app.conf.task_queues = existing_queues + (queue_def,)

#     # Use the queue definition which includes priority arguments
#     logger.info(f"Adding consumer for queue '{queue}' using definition with priority arguments")
#     consumer = state.consumer
#     if hasattr(consumer, "add_task_queue"):
#         consumer.add_task_queue(queue_def)
#         return {"ok": f"added consumer for queue '{queue}'"}
#     else:
#         # Fallback: try to create queue manually
#         logger.warning("Consumer does not have add_task_queue method, trying alternative approach")
#         try:
#             # Use the default implementation by creating a queue manually
#             from kombu import Exchange

#             ex = Exchange(exchange or queue, type=exchange_type or "direct")
#             q = Queue(
#                 queue,
#                 exchange=ex,
#                 routing_key=routing_key or queue,
#                 queue_arguments={"x-max-priority": configuration.settings.routing_max_priority + 1},
#             )
#             consumer.add_task_queue(q)
#             return {"ok": f"added consumer for queue '{queue}'"}
#         except Exception as e:
#             logger.error(f"Failed to add consumer for queue '{queue}': {e}", exc_info=True)
#             return {"error": str(e)}


# # Register the custom add_consumer command to override the default one
# # This must be done after celery_app is created
# Panel.register(add_consumer_with_priority, name="add_consumer")


# # Import tasks to ensure they are registered with Celery
# # This ensures that when the worker starts, all tasks are available
from api.tasks import routing  # noqa: F401,E402
