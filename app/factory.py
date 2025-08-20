import logging
from importlib import import_module

from fastapi import APIRouter, Depends, FastAPI, Request, Response
from fastapi.dependencies.utils import get_dependant
from prometheus_fastapi_instrumentator import Instrumentator
import sentry_sdk
from starlette.middleware.sessions import SessionMiddleware

from app.schemas.admin.roles import PermissionType
from app.schemas.core.context import RequestContext
from app.schemas.usage import Usage
from app.sql.session import set_get_db_func
from app.utils.context import generate_request_id, request_context
from app.utils.hooks_decorator import hooks
from app.utils.variables import (
    ROUTER__COMPLETIONS,
    ROUTER__FILES,
    ROUTER__MONITORING,
    ROUTER__OCR,
    ROUTERS,
)

logger = logging.getLogger(__name__)


def create_app(db_func=None, *args, **kwargs) -> FastAPI:
    """Create FastAPI application."""
    if db_func is not None:
        set_get_db_func(db_func)
    from app.utils.configuration import configuration
    from app.utils.lifespan import lifespan

    if configuration.dependencies.sentry:
        logger.info("Initializing Sentry SDK.")
        sentry_sdk.init(**configuration.dependencies.sentry.model_dump())

    app = FastAPI(
        title=configuration.settings.swagger_title,
        summary=configuration.settings.swagger_summary,
        version=configuration.settings.swagger_version,
        description=configuration.settings.swagger_description,
        terms_of_service=configuration.settings.swagger_terms_of_service,
        contact=configuration.settings.swagger_contact,
        licence_info=configuration.settings.swagger_license_info,
        openapi_tags=configuration.settings.swagger_openapi_tags,
        docs_url=configuration.settings.swagger_docs_url,
        redoc_url=configuration.settings.swagger_redoc_url,
        lifespan=lifespan,
    )
    app.add_middleware(SessionMiddleware, secret_key=configuration.settings.session_secret_key)

    from app.helpers._accesscontroller import AccessController

    def add_hooks(router: APIRouter) -> None:
        for route in router.routes:
            route.endpoint = hooks(route.endpoint)
            route.dependant = get_dependant(path=route.path_format, call=route.endpoint)

    @app.middleware("http")
    async def set_request_context(request: Request, call_next):
        """Middleware to set request context."""
        request_context.set(
            RequestContext(
                id=generate_request_id(),
                method=request.method,
                endpoint=request.url.path,
                client=request.client.host,
                usage=Usage(),
            )
        )

        return await call_next(request)

    # Routers
    for router in ROUTERS:
        prefix = "/v1"

        include_in_schema = router not in configuration.settings.hidden_routers and router not in configuration.settings.disabled_routers
        log_usage = True

        router_name = router.upper() if router == ROUTER__OCR else router.title()
        if router in [ROUTER__COMPLETIONS, ROUTER__FILES]:  # legacy routers
            router_name = "Legacy"
            include_in_schema = False
            log_usage = False

        if router == ROUTER__MONITORING:
            if configuration.settings.monitoring_prometheus_enabled:
                app.instrumentator = Instrumentator().instrument(app=app)
                app.instrumentator.expose(app=app, should_gzip=True, tags=[router_name], dependencies=[Depends(dependency=AccessController(permissions=[PermissionType.READ_METRIC]))], include_in_schema=include_in_schema)  # fmt: off

            @app.get(path="/health", tags=[router_name], include_in_schema=include_in_schema)
            def health() -> Response:
                return Response(status_code=200)

        else:
            try:
                module = import_module(f"app.endpoints.{router}")
                router_instance = getattr(module, "router")
            except Exception as e:
                logger.exception("Failed to import router module for %s: %s", router, e)
                continue

            if log_usage:
                add_hooks(router=router_instance)
            app.include_router(router=router_instance, tags=[router_name], prefix=prefix, include_in_schema=router_name != include_in_schema)

    return app
