from celery import Celery
from api.utils.configuration import configuration
from kombu import Queue

settings = configuration.settings

celery_app = Celery("albert")

# Base configuration
celery_app.conf.update(
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=settings.celery_task_eager_propagates,
    broker_url=settings.celery_broker_url,
    result_backend=settings.celery_result_backend,
    task_soft_time_limit=settings.celery_task_soft_time_limit,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Priority queues (RabbitMQ only). We lazily declare per-model queues elsewhere; here we set defaults.
MAX_PRIORITY = settings.celery_task_max_priority  # 0-(n-1) usable priorities (n levels)
if settings.celery_broker_url and settings.celery_broker_url.startswith("amqp://"):
    # Use a default catch-all queue with priority enabled; model-specific queues reuse same arguments.
    celery_app.conf.task_queues = (Queue("model.default", routing_key="model.default", queue_arguments={"x-max-priority": MAX_PRIORITY}),)
    celery_app.conf.task_default_queue = "model.default"
    celery_app.conf.task_default_exchange = ""
    celery_app.conf.task_default_routing_key = "model.default"
    celery_app.conf.task_queue_max_priority = MAX_PRIORITY


def queue_name_for_model(router_name: str) -> str:
    return f"{settings.celery_default_queue_prefix}{router_name}" if router_name else settings.celery_default_queue_prefix.rstrip(".")


def task_priority_from_user_priority(user_priority: int) -> int:
    """Map internal user priority (arbitrary int >=0) to Celery/RabbitMQ priority range 0-9.

    Strategy: clamp; higher user numbers don't exceed max. Leaves 0 as baseline.
    """
    return max(0, min(int(user_priority), MAX_PRIORITY - 1))


__all__ = ["celery_app", "queue_name_for_model", "task_priority_from_user_priority", "MAX_PRIORITY"]
