import logging

from celery import Celery
from celery.signals import worker_init
from kombu import Queue
from redis import ConnectionPool, Redis

from api.utils.configuration import configuration

settings = configuration.settings
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
        RuntimeError: If called before worker initialization (e.g., in eager mode without pool setup).
    """
    if _redis_pool is None:
        raise RuntimeError("Redis pool not initialized. This function should only be called within Celery tasks after worker initialization.")
    return Redis.from_pool(connection_pool=_redis_pool)


celery_app = Celery(main=configuration.settings.app_title)

# Base configuration
celery_app.conf.update(
    task_always_eager=configuration.settings.celery_task_always_eager,
    task_eager_propagates=configuration.settings.celery_task_eager_propagates,
    broker_url=configuration.settings.celery_broker_url,
    result_backend=configuration.settings.celery_result_backend,
    task_soft_time_limit=configuration.settings.celery_task_soft_time_limit,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_create_missing_queues=True,  # Enable dynamic queue creation
)

# Priority queues (RabbitMQ only). We lazily declare per-model queues elsewhere; here we set defaults.
if configuration.settings.celery_broker_url and configuration.settings.celery_broker_url.startswith("amqp://"):
    # Use a default catch-all queue with priority enabled; model-specific queues reuse same arguments.
    celery_app.conf.task_queues = (
        Queue(
            f"{configuration.settings.celery_default_queue_prefix}.default",
            routing_key=f"{configuration.settings.celery_default_queue_prefix}.default",
            queue_arguments={"x-max-priority": configuration.settings.celery_task_max_priority},
        ),
    )
    celery_app.conf.task_default_queue = f"{configuration.settings.celery_default_queue_prefix}.default"
    celery_app.conf.task_default_exchange = ""
    celery_app.conf.task_default_routing_key = f"{configuration.settings.celery_default_queue_prefix}.default"
    celery_app.conf.task_queue_max_priority = configuration.settings.celery_task_max_priority


def ensure_queue_exists(queue_name: str) -> None:
    """
    Ensure a queue exists with proper configuration (priority support for RabbitMQ).
    This function declares the queue if it doesn't exist yet, ensuring it has the correct
    arguments for priority queues when using RabbitMQ. With task_create_missing_queues=True,
    queues are created automatically when tasks are sent, but we still need to declare them
    with proper arguments for RabbitMQ priority queues.

    Args:
        queue_name: The name of the queue to ensure exists
    """
    if settings.celery_task_always_eager:
        return

    queue = Queue(queue_name, routing_key=queue_name, queue_arguments={"x-max-priority": configuration.settings.celery_task_max_priority})
    existing_queues = celery_app.conf.task_queues or ()
    queue_names = {q.name for q in existing_queues}
    if queue_name not in queue_names:
        celery_app.conf.task_queues = existing_queues + (queue,)
        celery_app.control.add_consumer(queue_name)


# Import tasks to ensure they are registered with Celery
# This ensures that when the worker starts, all tasks are available
from api.tasks import routing  # noqa: F401,E402
