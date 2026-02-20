import os

from fastapi import Depends, FastAPI
import prometheus_client
from prometheus_client import CollectorRegistry, multiprocess
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.responses import Response

from api.helpers._accesscontroller import AccessController
from api.schemas.admin.roles import PermissionType
from api.utils.variables import RouterName


def setup_prometheus(app: FastAPI, include_in_schema: bool = True) -> None:
    app.instrumentator = Instrumentator().instrument(app=app)

    @app.get(
        path="/metrics",
        tags=[RouterName.MONITORING.title()],
        dependencies=[Depends(dependency=AccessController(permissions=[PermissionType.READ_METRIC]))],
        include_in_schema=include_in_schema,
    )
    def metrics() -> Response:
        if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
            registry = CollectorRegistry()
            multiprocess.MultiProcessCollector(registry)
        else:
            registry = prometheus_client.REGISTRY

        data = prometheus_client.generate_latest(registry)
        return Response(content=data, media_type=prometheus_client.CONTENT_TYPE_LATEST)
