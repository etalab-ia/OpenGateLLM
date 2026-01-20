from fastapi import APIRouter, Body, Depends, Security

from api.dependencies import create_router_use_case, get_request_context
from api.infrastructure.fastapi.access import get_current_key
from api.infrastructure.fastapi.context import RequestContext
from api.infrastructure.fastapi.endpoints.exceptions import (
    InsufficientPermissionHTTPException,
    InternalServerHTTPException,
    RouterAliasAlreadyExistsHTTPException,
    RouterAlreadyExistsHTTPException,
)
from api.infrastructure.fastapi.schemas.routers import CreateRouter, CreateRouterResponse
from api.main import logger
from api.use_cases.admin import (
    CreateRouterUseCase,
    CreateRouterUseCaseSuccess,
    InsufficientPermissionError,
    RouterAliasAlreadyExistsError,
    RouterNameAlreadyExistsError,
)
from api.utils.variables import ENDPOINT__ADMIN_ROUTERS, ROUTER__ADMIN

router = APIRouter(prefix="/v1", tags=[ROUTER__ADMIN.title()])


@router.post(path=ENDPOINT__ADMIN_ROUTERS, dependencies=[Security(dependency=get_current_key)], status_code=201)
async def create_router(
    body: CreateRouter = Body(description="The router creation request."),
    create_router_use_case: CreateRouterUseCase = Depends(create_router_use_case),
    request_context: RequestContext = Depends(get_request_context),
) -> CreateRouterResponse:
    """
    Create a router (without any providers).
    """
    try:
        result = await create_router_use_case.execute(
            user_id=request_context.get().user_id,
            name=body.name,
            router_type=body.type,
            aliases=body.aliases,
            load_balancing_strategy=body.load_balancing_strategy,
            cost_prompt_tokens=body.cost_prompt_tokens,
            cost_completion_tokens=body.cost_completion_tokens,
        )
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
            return CreateRouterResponse.model_validate(created_router.model_dump())
        case RouterAliasAlreadyExistsError():
            raise RouterAliasAlreadyExistsHTTPException()
        case RouterNameAlreadyExistsError(name):
            raise RouterAlreadyExistsHTTPException(name)
        case InsufficientPermissionError():
            raise InsufficientPermissionHTTPException()
