import logging

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
    ROUTER__ADMIN,
    ROUTER__COMPLETIONS,
    ROUTER__FILES,
    ROUTER__MONITORING,
    ROUTER__OAUTH2,
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

    # Set up database dependency
    # If no db_func provided, the depends module will fall back to default
    from app.endpoints import (
        agents,  # noqa: F401
        audio,  # noqa: F401
        auth,  # noqa: F401
        chat,  # noqa: F401
        chunks,  # noqa: F401
        collections,  # noqa: F401
        completions,  # noqa: F401
        deepsearch,  # noqa: F401
        documents,  # noqa: F401
        embeddings,  # noqa: F401
        files,  # noqa: F401
        models,  # noqa: F401
        ocr,  # noqa: F401
        parse,  # noqa: F401
        proconnect,
        rerank,  # noqa: F401
        search,  # noqa: F401
        tokens,  # noqa: F401
        usage,  # noqa: F401
    )
    from app.endpoints.admin import roles as admin_roles
    from app.endpoints.admin import tokens as admin_tokens
    from app.endpoints.admin import users as admin_users
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

        include_in_schema = router not in configuration.settings.hidden_routers
        if router in configuration.settings.disabled_routers:
            include_in_schema = False

        router_name = router.upper() if router == ROUTER__OCR else router.title()

        if router == ROUTER__ADMIN:
            add_hooks(router=admin_roles.router)
            app.include_router(router=admin_roles.router, tags=[router_name], prefix=prefix, include_in_schema=include_in_schema)

            add_hooks(router=admin_tokens.router)
            app.include_router(router=admin_tokens.router, tags=[router_name], prefix=prefix, include_in_schema=include_in_schema)

            add_hooks(router=admin_users.router)
            app.include_router(router=admin_users.router, tags=[router_name], prefix=prefix, include_in_schema=include_in_schema)

        elif router == ROUTER__MONITORING:
            if configuration.settings.monitoring_prometheus_enabled:
                app.instrumentator = Instrumentator().instrument(app=app)
                app.instrumentator.expose(app=app, should_gzip=True, tags=[router_name], dependencies=[Depends(dependency=AccessController(permissions=[PermissionType.READ_METRIC]))], include_in_schema=include_in_schema)  # fmt: off

            @app.get(path="/health", tags=[router_name], include_in_schema=include_in_schema)
            def health() -> Response:
                return Response(status_code=200)

        elif router in [ROUTER__COMPLETIONS, ROUTER__FILES]:  # legacy routers
            include_in_schema = False
            router_name = "Legacy"
            app.include_router(router=locals()[router].router, tags=[router_name], prefix=prefix, include_in_schema=include_in_schema)

        elif router == ROUTER__OAUTH2:
            add_hooks(router=proconnect.router)
            app.include_router(router=proconnect.router, tags=[router_name], prefix=prefix, include_in_schema=include_in_schema)

        else:
            add_hooks(router=locals()[router].router)
            app.include_router(router=locals()[router].router, tags=[router_name], prefix=prefix, include_in_schema=include_in_schema)

    return app
