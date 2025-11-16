import logging

from celery import Celery
from celery.signals import worker_init
from kombu import Queue
from redis import ConnectionPool, Redis

from api.utils.configuration import configuration
from api.utils.variables import PREFIX__CELERY_QUEUE_ROUTING

logger = logging.getLogger(__name__)

# Redis connection pool - initialized when worker starts
_redis_pool = None


@worker_init.connect
def init_redis_pool(**kwargs):
    """Initialize Redis connection pool when Celery worker starts."""
    global _redis_pool
    _redis_pool = ConnectionPool.from_url(url=configuration.dependencies.redis.url)
    logger.info("Redis connection pool initialized for Celery worker")


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


app = Celery(main=configuration.settings.app_title)
app.autodiscover_tasks(packages=["api.tasks.routing"])

# Configure Celery - use celery dependency if available, otherwise fallback to Redis
if configuration.dependencies.celery is not None:
    app.conf.update(
        broker_url=configuration.dependencies.celery.broker_url,
        result_backend=configuration.dependencies.celery.result_backend,
        timezone=configuration.dependencies.celery.timezone,
        enable_utc=configuration.dependencies.celery.enable_utc,
        task_max_priority=configuration.settings.routing_max_priority,
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        task_create_missing_queues=True,
        task_default_routing_key=f"{PREFIX__CELERY_QUEUE_ROUTING}.default",
        task_queues=(
            Queue(
                name=f"{PREFIX__CELERY_QUEUE_ROUTING}.default",
                routing_key=f"{PREFIX__CELERY_QUEUE_ROUTING}.default",
                queue_arguments={"x-max-priority": configuration.settings.routing_max_priority + 1},
            ),
        ),
        task_default_queue=f"{PREFIX__CELERY_QUEUE_ROUTING}.default",
        task_default_exchange="",
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
    existing_queues = app.conf.task_queues or ()
    queue_names = {q.name for q in existing_queues}
    if queue_name not in queue_names:
        app.conf.task_queues = existing_queues + (queue,)

    # Declare the queue explicitly on the broker with its arguments
    with app.connection() as conn:
        channel = conn.channel()
        queue.declare(channel=channel)

    # Dynamically subscribe all active workers to this queue
    inspect = app.control.inspect()
    active_workers = inspect.active()
    if active_workers:
        worker_names = list(active_workers.keys())
        logger.info(f"Subscribing {len(worker_names)} active worker(s) to queue '{queue_name}'")
        app.control.add_consumer(queue_name, destination=worker_names)
