from typing import Any, Dict

from api.helpers.models.routers._modelrouter import ModelRouter
from billiard.exceptions import SoftTimeLimitExceeded
from celery.exceptions import Retry, MaxRetriesExceededError

from api.tasks.celery_app import celery_app
from api.schemas.core.configuration import Model as ModelRouterSchema
from api.utils.configuration import configuration

settings = configuration.settings


@celery_app.task(name="model.invoke", bind=True)
def invoke_model_task(self, router_schema: Dict[str, Any], endpoint: str) -> Dict[str, Any]:
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
        return {"status_code": 504, "body": {"detail": "Model invocation exceeded the soft time limit"}}
    except Exception as e:  # pragma: no cover - defensive
        return {"status_code": 500, "body": {"detail": type(e).__name__}}
