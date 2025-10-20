from typing import Any, Dict

from billiard.exceptions import SoftTimeLimitExceeded
from celery.exceptions import MaxRetriesExceededError, Retry

from api.helpers.models.routers._modelrouter import ModelRouter
from billiard.exceptions import SoftTimeLimitExceeded
from celery.exceptions import Retry, MaxRetriesExceededError

from api.tasks.celery_app import celery_app, shared_queue_name_from_private_one
from api.schemas.core.configuration import Model as ModelRouterSchema
from api.tasks.celery_app import celery_app
from api.utils.configuration import configuration

settings = configuration.settings


@celery_app.task(name="model.invoke.shared", bind=True)
def invoke_shared_model_task(self, router_schema: Dict[str, Any], endpoint: str) -> Dict[str, Any]:
    """Invoke a model provider (non-streaming).

    router_schema: serialized ModelRouterSchema schema (censored=False)

    Returns: {"status_code": int, "body": dict}
    """

    # Reconstruct Pydantic Model from dict
    try:
        schema_obj = ModelRouterSchema(**router_schema)
    except Exception:
        # Backward compatibility: router_schema may use 'name' instead of 'model_name'
        if "name" in router_schema and "model_name" not in router_schema:
            router_schema["model_name"] = router_schema["name"]
        schema_obj = ModelRouterSchema(**router_schema)

    router = ModelRouter.from_schema(schema=schema_obj)

    try:
        client, performance_indicator = router.get_client(endpoint=endpoint)
        can_be_forwarded = client.apply_modelclient_policy(performance_indicator)
        if can_be_forwarded:
            return {
                "status_code": 200,
                "client": client.as_schema(censored=False).model_dump(),
                "cycle_offset": router._cycle.offset,
                "requeue_count": self.request.retries,
                "performance_indicator": performance_indicator,
            }
        else:
            raise self.retry(
                countdown=settings.celery_task_retry_countdown,
                max_retries=settings.celery_task_max_retry,
            )

    except Retry:
        raise
    except MaxRetriesExceededError:
        return {"status_code": 503, "requeue_count": self.request.retries, "body": {"detail": "Max retries exceeded"}}
    except SoftTimeLimitExceeded:
        return {"status_code": 504, "requeue_count": self.request.retries, "body": {"detail": "Model invocation exceeded the soft time limit"}}
    except Exception as e:  # pragma: no cover - defensive
        return {"status_code": 500, "requeue_count": self.request.retries, "body": {"detail": type(e).__name__}}


@celery_app.task(name="model.invoke.private", bind=True)
def invoke_private_model_task(self, router_schema: Dict[str, Any], endpoint: str, mode: str, organization: str) -> Dict[str, Any]:
    """
    Private or private-first invocation for a specific provider.
    mode ∈ {"private", "private-first"}
    """

    # Reconstruct Pydantic Model from dict
    try:
        schema_obj = ModelRouterSchema(**router_schema)
    except Exception:
        # Backward compatibility: router_schema may use 'name' instead of 'model_name'
        if "name" in router_schema and "model_name" not in router_schema:
            router_schema["model_name"] = router_schema["name"]
        schema_obj = ModelRouterSchema(**router_schema)

    router = ModelRouter.from_schema(schema=schema_obj)

    try:
        client, performance_indicator = router.get_client_from_org(organization, endpoint=endpoint)
        can_be_forwarded = client.apply_modelclient_policy(performance_indicator)

        if can_be_forwarded:
            return {
                "status_code": 200,
                "client": client.as_schema(censored=False).model_dump(),
                "cycle_offset": router._cycle.offset,
                "requeue_count": self.request.retries,
                "performance_indicator": performance_indicator,
            }

        elif mode == "private-first":
            current_queue = self.request.delivery_info.get("routing_key", "")
            shared_queue = shared_queue_name_from_private_one(current_queue)

            invoke_shared_model_task.apply_async(
                args=[router_schema, endpoint],
                queue=shared_queue,
                priority=self.request.delivery_info.get("priority", 0),
            )

            return {
                "status_code": 202,
                "body": {"detail": f"Requeued from {current_queue} → {shared_queue}"},
            }

        else:
            raise self.retry(
                countdown=settings.celery_task_retry_countdown,
                max_retries=settings.celery_task_max_retry,
            )

    except Retry:
        raise
    except MaxRetriesExceededError:
        return {"status_code": 503, "body": {"detail": "Max retries exceeded"}}
    except SoftTimeLimitExceeded:
        return {"status_code": 504, "body": {"detail": "Soft time limit exceeded"}}
    except Exception as e:
        return {"status_code": 500, "body": {"detail": type(e).__name__}}
