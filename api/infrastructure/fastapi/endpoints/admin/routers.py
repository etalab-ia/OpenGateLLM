import logging

from fastapi import Body, Depends, Security

from api.dependencies import create_router_use_case, get_request_context
from api.domain.router.errors import RouterAliasAlreadyExistsError, RouterNameAlreadyExistsError
from api.domain.userinfo.errors import InsufficientPermissionError
from api.infrastructure.fastapi.access import get_current_key
from api.infrastructure.fastapi.context import RequestContext
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.admin import router
from api.infrastructure.fastapi.endpoints.exceptions import (
    InsufficientPermissionHTTPException,
    InternalServerHTTPException,
    RouterAliasAlreadyExistsHTTPException,
    RouterAlreadyExistsHTTPException,
)
from api.infrastructure.fastapi.schemas.routers import CreateRouter, CreateRouterResponse
from api.use_cases.admin import CreateRouterCommand, CreateRouterUseCase, CreateRouterUseCaseSuccess
from api.utils.variables import EndpointRoute

logger = logging.getLogger(__name__)


@router.post(
    path=EndpointRoute.ADMIN_ROUTERS,
    dependencies=[Security(dependency=get_current_key)],
    status_code=201,
    responses=get_documentation_responses([
        RouterAliasAlreadyExistsHTTPException,
        RouterAlreadyExistsHTTPException,
        InsufficientPermissionHTTPException,
    ]),
)
async def create_router(
    body: CreateRouter = Body(description="The router creation request."),
    create_router_use_case: CreateRouterUseCase = Depends(create_router_use_case),
    request_context: RequestContext = Depends(get_request_context),
) -> CreateRouterResponse:
    """
    Create a router (without any providers).
    """
    try:
        command = CreateRouterCommand(
            user_id=request_context.get().user_id,
            name=body.name,
            router_type=body.type,
            aliases=body.aliases,
            load_balancing_strategy=body.load_balancing_strategy,
            cost_prompt_tokens=body.cost_prompt_tokens,
            cost_completion_tokens=body.cost_completion_tokens,
        )
        result = await create_router_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing create_router use case",
            extra={
                "user_id": request_context.get().user_id,
                "router_name": body.name,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()

    match result:
        case CreateRouterUseCaseSuccess(created_router):
            return CreateRouterResponse.model_validate(created_router, from_attributes=True)
        case RouterAliasAlreadyExistsError(name):
            raise RouterAliasAlreadyExistsHTTPException(name)
        case RouterNameAlreadyExistsError(name):
            raise RouterAlreadyExistsHTTPException(name)
        case InsufficientPermissionError():
            raise InsufficientPermissionHTTPException()
