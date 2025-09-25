from __future__ import annotations
from typing import Any, Dict

import asyncio
import logging


from api.tasks.celery_app import celery_app
from api.utils.configuration import configuration
from api.utils.context import global_context
from api.schemas.core.configuration import ModelProvider as ModelClientSchema
from api.clients.model import BaseModelClient
from api.tasks.model import invoke_model_task
from api.tasks.celery_app import queue_name_for_model, task_priority_from_user_priority
from api.utils.tracked_cycle import TrackedCycle
from api.utils.exceptions import TaskFailedException

logger = logging.getLogger(__name__)

settings = configuration.settings


async def invoke_model_request(
    model_name: str,
    endpoint: str,
    user_priority: int | None = None,
) -> BaseModelClient:
    """Invoke a model (non-streaming) returning (status_code, json_body).

    Decides between direct async path (eager) and Celery task submission.
    """
    router = await global_context.model_registry(model=model_name)

    # Eager path: stay fully async
    if settings.celery_task_always_eager:
        async with router._lock:
            client, _ = router.get_client(endpoint=endpoint)
        return client

    # Celery path
    router_schema = (await router.as_schema(censored=False)).model_dump()
    # Ensure we always enqueue on the canonical router name (an alias would create a queue the worker might not consume)
    try:
        original_name = await global_context.model_registry.get_original_name(model_name)
    except Exception:
        original_name = model_name  # fallback; error will surface later if invalid

    queue = queue_name_for_model(original_name)
    priority = task_priority_from_user_priority(user_priority or 0)

    # Submit task
    async_result = invoke_model_task.apply_async(args=[router_schema, endpoint], queue=queue, priority=priority)

    # Wait for result using async polling
    result = await wait_for_task_result(async_result.id)

    if result["status_code"] != 200:
        raise TaskFailedException(status_code=result["status_code"], detail=result["body"]["detail"])

    router._cycle.offset = result["cycle_offset"]
    router._cycle = TrackedCycle(router._cycle.items, router._cycle.offset)
    client_schema = result["client"]

    try:
        schema_obj = ModelClientSchema(**client_schema)
    except Exception:
        # Backward compatibility: client_schema may use 'name' instead of 'model_name'
        if "name" in client_schema and "model_name" not in client_schema:
            client_schema["model_name"] = client_schema["name"]
        schema_obj = ModelClientSchema(**client_schema)

    client = BaseModelClient.from_schema(schema=schema_obj)
    return client


async def wait_for_task_result(task_id: str, timeout: int = settings.celery_task_soft_time_limit, poll_interval: float = 0.1) -> Dict[str, Any]:
    """Wait for task result using async polling to avoid blocking and connection issues."""
    from celery.result import AsyncResult

    async_result = AsyncResult(task_id, app=celery_app)
    loop = asyncio.get_event_loop()
    start_time = loop.time()

    # Poll until the task is ready or timeout is reached
    while not async_result.ready():
        if loop.time() - start_time > timeout:
            raise TimeoutError(f"Task {task_id} timed out after {timeout} seconds")
        await asyncio.sleep(poll_interval)

    # Once ready, safely retrieve the result
    try:
        return async_result.result  # Direct access is safe after ready() returns True
    except Exception as e:
        logger.warning(f"Error retrieving result for task {task_id}: {e}")
        raise


__all__ = ["invoke_model_request"]
