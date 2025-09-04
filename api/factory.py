import logging
import pkgutil
from importlib import import_module

from fastapi import APIRouter, Depends, FastAPI, Request, Response
from fastapi.dependencies.utils import get_dependant
from prometheus_fastapi_instrumentator import Instrumentator
import sentry_sdk
from starlette.middleware.sessions import SessionMiddleware

from api.schemas.admin.roles import PermissionType
from api.schemas.core.context import RequestContext
from api.schemas.usage import Usage
from api.sql.session import set_get_db_func
from api.utils.context import generate_request_id, request_context
from api.utils.hooks_decorator import hooks
from api.utils.variables import (
    ROUTER__COMPLETIONS,
    ROUTER__FILES,
    ROUTER__MONITORING,
    ROUTER__OCR,
)

logger = logging.getLogger(__name__)


def create_app(db_func=None, *args, **kwargs) -> FastAPI:
    """Create FastAPI application."""
    if db_func is not None:
        set_get_db_func(db_func)
    from api.utils.configuration import configuration
    from api.utils.lifespan import lifespan

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

    from api.helpers._accesscontroller import AccessController

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

    # Routers: dynamic discovery of modules under app.endpoints
    prefix = "/v1"

    def iter_endpoint_modules():
        """Yield (key, module) for each importable module/package under app.endpoints that defines a router."""
        base_pkg_name = "api.endpoints"
        try:
            base_pkg = import_module(base_pkg_name)
            for finder, name, ispkg in pkgutil.walk_packages(base_pkg.__path__, base_pkg.__name__ + "."):
                # Skip private modules
                short = name[len(base_pkg_name) + 1 :]
                if not short or short.split(".")[-1].startswith("_"):
                    continue

                # Respect disabled routers by key match (e.g., "auth", "proconnect", "admin.organizations")
                key = short
                # Only include modules that are not disabled entirely by their top-level key
                top_key = key.split(".")[0]
                if top_key in configuration.settings.disabled_routers or key in configuration.settings.disabled_routers:
                    continue

                try:
                    mod = import_module(name)
                except Exception as e:
                    logger.exception("Failed to import endpoint module %s: %s", name, e)
                    continue

                if hasattr(mod, "router"):
                    yield key, mod
        except Exception as e:
            logger.exception("Failed to iterate endpoint modules: %s", e)

    for key, mod in iter_endpoint_modules():
        # Special-case monitoring remains as-is
        if key == ROUTER__MONITORING:
            include_in_schema = key not in configuration.settings.hidden_routers
            if configuration.settings.monitoring_prometheus_enabled:
                app.instrumentator = Instrumentator().instrument(app=app)
                app.instrumentator.expose(app=app, should_gzip=True, tags=["Monitoring"], dependencies=[Depends(dependency=AccessController(permissions=[PermissionType.READ_METRIC]))], include_in_schema=include_in_schema)  # fmt: off

            @app.get(path="/health", tags=["Monitoring"], include_in_schema=include_in_schema)
            def health() -> Response:
                return Response(status_code=200)

            continue

        try:
            router_instance = getattr(mod, "router")
        except Exception as e:
            logger.exception("Module %s has no router or failed to access it: %s", key, e)
            continue

        # Decide router tag and include_in_schema
        router_name = getattr(mod, "ROUTER_NAME", None)
        if not router_name:
            # Use OCR upper-case name for the ocr module
            router_name = key.upper() if key == ROUTER__OCR else key.split(".")[-1].title()

        include_in_schema = key not in configuration.settings.hidden_routers and key.split(".")[0] not in configuration.settings.hidden_routers

        # Legacy: disable usage hooks and hide docs for legacy routers
        log_usage = True
        if key in [ROUTER__COMPLETIONS, ROUTER__FILES] or key.split(".")[0] in [ROUTER__COMPLETIONS, ROUTER__FILES]:
            router_name = "Legacy"
            include_in_schema = False
            log_usage = False

        if log_usage:
            add_hooks(router=router_instance)

        try:
            app.include_router(router=router_instance, tags=[router_name], prefix=prefix, include_in_schema=include_in_schema)
        except Exception as e:
            logger.exception("Failed to include router for %s: %s", key, e)

    return app
