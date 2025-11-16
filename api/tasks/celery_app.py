import logging

from celery import Celery
from celery.signals import worker_init
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


def get_redis_client() -> Redis:
    """
    Get a synchronous Redis client for use in Celery tasks.

    Returns:
        Redis: A synchronous Redis client instance.

    Raises:
        RuntimeError: If called before worker initialization (e.g., in eager mode without pool setup).
    """
    if _redis_pool is None:
        raise RuntimeError("Redis pool not initialized. This function should only be called within Celery tasks after worker initialization.")
    return Redis.from_pool(connection_pool=_redis_pool)


celery_app = Celery(main=configuration.settings.app_title)
# Alias for imports and worker startup script


# Base configuration
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
    task_create_missing_queues=True,  # Enable dynamic queue creation
)


def ensure_queue_exists(queue_name: str) -> None:
    """
    Ensure a queue exists with proper configuration (priority support for RabbitMQ).
    This function declares the queue with priority arguments, even if it already exists.
    This ensures that queues created automatically by task_create_missing_queues=True
    are properly configured with priority support.

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

    # Force declaration of the queue in RabbitMQ with priority arguments
    # This will update existing queues or create new ones with the correct arguments
    try:
        with celery_app.connection() as conn:
            queue.declare(channel=conn.channel())
            logger.debug(f"Queue '{queue_name}' declared with priority support (x-max-priority={configuration.settings.routing_max_priority + 1})")
    except Exception as e:
        logger.warning(f"Failed to declare queue '{queue_name}' with priority arguments: {e}")
        # Fallback: try to add consumer (for worker processes)
        try:
            celery_app.control.add_consumer(queue_name)
        except Exception:
            pass


# Import tasks to ensure they are registered with Celery
# This ensures that when the worker starts, all tasks are available
from api.tasks import routing  # noqa: F401,E402
