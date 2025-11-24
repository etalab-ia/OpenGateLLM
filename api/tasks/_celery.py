import logging

from celery import Celery
from celery.signals import worker_init
from kombu import Exchange, Queue
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

if configuration.dependencies.celery is not None:
    app.conf.update(
        broker_url=configuration.dependencies.celery.broker_url,
        result_backend=configuration.dependencies.celery.result_backend,
        timezone=configuration.dependencies.celery.timezone,
        enable_utc=configuration.dependencies.celery.enable_utc,
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        task_queues=[],
    )


def create_model_queue(queue_name: str) -> Queue:
    """Create a Celery Queue object for a specific model with priority support"""
    model_exchange = Exchange("llm_models", type="direct", durable=True)
    return Queue(
        queue_name,
        exchange=model_exchange,
        routing_key=queue_name,
        queue_arguments={"x-max-priority": configuration.settings.routing_max_priority + 1},
        durable=True,
    )


def add_model_queue_to_running_worker(queue_name: str):
    """
    Add a new model queue to already running workers.
    This is called from the API when a new model is registered.
    """
    if configuration.dependencies.celery is None:
        return
    app.control.add_consumer(
        queue=queue_name,
        exchange="llm_models",
        exchange_type="direct",
        routing_key=queue_name,
        options={"queue_arguments": {"x-max-priority": configuration.settings.routing_max_priority + 1}},
    )
