from importlib import import_module
import logging
import pkgutil

from fastapi import Depends, FastAPI, Request
from prometheus_fastapi_instrumentator import Instrumentator
import sentry_sdk
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import JSONResponse

from api.helpers._accesscontroller import AccessController
from api.schemas.admin.roles import PermissionType
from api.schemas.core.context import RequestContext
from api.schemas.usage import Usage
from api.utils.configuration import configuration
from api.utils.context import generate_request_id, request_context
from api.utils.lifespan import lifespan
from api.utils.variables import ROUTER__MONITORING

logger = logging.getLogger(__name__)

if configuration.dependencies.sentry:
    logger.info("Initializing Sentry SDK.")
    sentry_sdk.init(**configuration.dependencies.sentry.model_dump())

app = FastAPI(
    title=configuration.settings.app_title,
    summary=configuration.settings.swagger_summary,
    version=configuration.settings.swagger_version,
    description=configuration.settings.swagger_description,
    terms_of_service=configuration.settings.swagger_terms_of_service,
    contact=configuration.settings.swagger_contact,
    license_info=configuration.settings.swagger_license_info,
    openapi_tags=configuration.settings.swagger_openapi_tags,
    docs_url=configuration.settings.swagger_docs_url,
    redoc_url=configuration.settings.swagger_redoc_url,
    lifespan=lifespan,
)
app.add_middleware(SessionMiddleware, secret_key=configuration.settings.session_secret_key)


@app.middleware("http")
async def set_request_context(request: Request, call_next):
    """Middleware to set request context."""
    request_context.set(
        RequestContext(
            id=generate_request_id(),
            user_info=None,
            token_id=None,
            router_id=None,
            provider_id=None,
            method=request.method,
            endpoint=request.url.path,
            usage=Usage(),
        )
    )

    return await call_next(request)


# add routers to the app
base_pkg = import_module(name="api.endpoints")
for finder, name, ispkg in pkgutil.walk_packages(base_pkg.__path__, base_pkg.__name__ + "."):
    router_name = name.split(".")[2]

    # disabled routers
    if router_name in configuration.settings.disabled_routers:
        continue

    module = import_module(name)
    if hasattr(module, "router"):
        # hidden routers
        if router_name in configuration.settings.hidden_routers:
            module.router.include_in_schema = False

        app.include_router(router=module.router, include_in_schema=module.router.include_in_schema)

# add monitoring router to the app
if ROUTER__MONITORING not in configuration.settings.disabled_routers:
    include_in_schema = ROUTER__MONITORING not in configuration.settings.hidden_routers
    if configuration.settings.monitoring_prometheus_enabled:
        app.instrumentator = Instrumentator().instrument(app=app)
        app.instrumentator.expose(app=app, should_gzip=True, tags=[ROUTER__MONITORING.title()], dependencies=[Depends(dependency=AccessController(permissions=[PermissionType.READ_METRIC]))], include_in_schema=include_in_schema)  # fmt: off

    @app.get(path="/health", tags=[ROUTER__MONITORING.title()], include_in_schema=include_in_schema)
    def health() -> JSONResponse:
        return JSONResponse(content={"status": "ok"}, status_code=200)
