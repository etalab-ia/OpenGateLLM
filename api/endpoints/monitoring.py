from fastapi import Depends, FastAPI
import prometheus_client
from prometheus_client import CollectorRegistry, multiprocess
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from starlette.responses import Response

from api.helpers._accesscontroller import AccessController
from api.schemas.admin.roles import PermissionType
from api.utils.configuration import configuration
from api.utils.monitoring import (
    inference_output_tokens_per_second,
    inference_requests_duration_seconds,
    inference_requests_total,
    inference_tokens_total,
    inference_ttft_milliseconds,
)
from api.utils.variables import RouterName


def setup_prometheus(app: FastAPI, metric_namespace: str = "ogl", include_in_schema: bool = True) -> None:
    app.instrumentator = (
        Instrumentator()
        .instrument(app=app)
        .add(
            metrics.default(metric_namespace=metric_namespace),
            inference_output_tokens_per_second(metric_namespace=metric_namespace),
            inference_requests_total(metric_namespace=metric_namespace),
            inference_requests_duration_seconds(metric_namespace=metric_namespace),
            inference_ttft_milliseconds(metric_namespace=metric_namespace),
            inference_tokens_total(metric_namespace=metric_namespace),
        )
        .expose(app)
    )

    @app.get(
        path="/metrics",
        tags=[RouterName.MONITORING.title()],
        dependencies=[Depends(dependency=AccessController(permissions=[PermissionType.READ_METRIC]))],
        include_in_schema=include_in_schema,
    )
    def get_metrics() -> Response:
        if configuration.prometheus_multiproc_dir:
            registry = CollectorRegistry()
            multiprocess.MultiProcessCollector(registry)
        else:
            registry = prometheus_client.REGISTRY

        data = prometheus_client.generate_latest(registry)
        return Response(content=data, media_type=prometheus_client.CONTENT_TYPE_LATEST)
