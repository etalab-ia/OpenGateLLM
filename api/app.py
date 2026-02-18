from importlib import import_module
import logging

from fastapi import FastAPI, Request
import sentry_sdk
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import JSONResponse

from api.endpoints.monitoring import setup_prometheus
from api.schemas.core.context import RequestContext
from api.schemas.usage import Usage
from api.utils.configuration import Configuration, get_configuration
from api.utils.context import request_context
from api.utils.lifespan import lifespan
from api.utils.variables import RouterName

logger = logging.getLogger(__name__)


def create_app(
    configuration: Configuration | None = None,
    skip_lifespan: bool = False,
) -> FastAPI:
    if configuration is None:
        configuration = get_configuration()

    _setup_sentry(configuration)

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
        lifespan=None if skip_lifespan else lifespan,
    )

    _setup_middleware(app, configuration)
    _register_routers(app, configuration)
    _setup_monitoring(app, configuration)

    return app


def _setup_sentry(configuration: Configuration) -> None:
    if configuration.dependencies.sentry:
        logger.info("Initializing Sentry SDK.")
        sentry_sdk.init(**configuration.dependencies.sentry.model_dump())


def _setup_middleware(app: FastAPI, configuration: Configuration) -> None:
    app.add_middleware(SessionMiddleware, secret_key=configuration.settings.session_secret_key)

    @app.middleware("http")
    async def set_request_context(request: Request, call_next):
        request_context.set(RequestContext(method=request.method, endpoint=request.url.path, usage=Usage()))
        return await call_next(request)


def _register_routers(app: FastAPI, configuration: Configuration) -> None:
    disabled_routers = set(configuration.settings.disabled_routers)
    hidden_routers = set(configuration.settings.hidden_routers)
    enabled_routers = (router for router in RouterName if router not in disabled_routers and router.module_path is not None)
    for enabled_router in enabled_routers:
        module = import_module(enabled_router.module_path)
        router = getattr(module, "router", None)
        if router is None:
            raise AttributeError(f"Module {enabled_router.module_path} has no 'router' attribute")
        include_in_schema = enabled_router not in hidden_routers
        app.include_router(router=router, include_in_schema=include_in_schema)

    # @TODO: legacy import before total clean archi migration
    # @TODO: create admin folder in infrastructure.fastapi.endpoints with router declaration in __init__.py
    if RouterName.ADMIN not in disabled_routers:
        module = import_module("api.infrastructure.fastapi.endpoints.admin_router")
        app.include_router(router=module.router, include_in_schema=RouterName.ADMIN not in hidden_routers)


def _setup_monitoring(app: FastAPI, configuration: Configuration) -> None:
    if RouterName.MONITORING in configuration.settings.disabled_routers:
        return

    include_in_schema = RouterName.MONITORING not in configuration.settings.hidden_routers

    if configuration.settings.monitoring_prometheus_enabled:
        setup_prometheus(app, include_in_schema=include_in_schema)

    @app.get(path="/health", tags=[RouterName.MONITORING.title()], include_in_schema=include_in_schema)
    def health() -> JSONResponse:
        return JSONResponse(content={"status": "ok"}, status_code=200)
