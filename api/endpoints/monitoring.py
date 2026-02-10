from fastapi import Depends, FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from api.helpers._accesscontroller import AccessController
from api.schemas.admin.roles import PermissionType
from api.utils.variables import RouterName


def setup_prometheus(app: FastAPI, include_in_schema: bool = True) -> None:
    app.instrumentator = Instrumentator().instrument(app=app)
    app.instrumentator.expose(
        app=app,
        should_gzip=True,
        tags=[RouterName.MONITORING.title()],
        dependencies=[Depends(dependency=AccessController(permissions=[PermissionType.READ_METRIC]))],
        include_in_schema=include_in_schema,
    )
