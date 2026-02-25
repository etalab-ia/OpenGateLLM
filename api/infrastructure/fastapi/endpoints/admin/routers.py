from contextvars import ContextVar
import logging

from fastapi import Body, Depends, Path, Query, Security

from api.dependencies import (
    create_router_use_case_factory,
    delete_router_use_case_factory,
    get_one_router_use_case_factory,
    get_request_context,
    get_routers_use_case_factory,
)
from api.domain.router.entities import RouterSortField, SortOrder
from api.domain.router.errors import RouterAliasAlreadyExistsError, RouterNameAlreadyExistsError, RouterNotFoundError
from api.domain.userinfo.errors import UserIsNotAdminError
from api.infrastructure.fastapi.access import get_current_key
from api.infrastructure.fastapi.context import RequestContext
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.admin import router
from api.infrastructure.fastapi.endpoints.exceptions import (
    InternalServerHTTPException,
    NotAdminUserHTTPException,
    RouterAliasAlreadyExistsHTTPException,
    RouterAlreadyExistsHTTPException,
    RouterNotFoundHTTPException,
)
from api.infrastructure.fastapi.schemas.routers import CreateRouter, CreateRouterResponse, Router, Routers
from api.use_cases.admin.routers import (
    CreateRouterCommand,
    CreateRouterUseCase,
    CreateRouterUseCaseSuccess,
    DeleteRouterCommand,
    DeleteRouterUseCase,
    DeleteRouterUseCaseSuccess,
    GetOneRouterCommand,
    GetOneRouterUseCase,
    GetOneRouterUseCaseSuccess,
    GetRoutersCommand,
    GetRoutersUseCase,
    GetRoutersUseCaseSuccess,
)
from api.utils.variables import EndpointRoute

logger = logging.getLogger(__name__)


@router.post(
    path=EndpointRoute.ADMIN_ROUTERS,
    dependencies=[Security(dependency=get_current_key)],
    status_code=201,
    responses=get_documentation_responses(
        [
            RouterAliasAlreadyExistsHTTPException,
            RouterAlreadyExistsHTTPException,
            NotAdminUserHTTPException,
        ]
    ),
)
async def create_router(
    body: CreateRouter = Body(description="The router creation request."),
    create_router_use_case: CreateRouterUseCase = Depends(create_router_use_case_factory),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> CreateRouterResponse:
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
        case UserIsNotAdminError():
            raise NotAdminUserHTTPException()


@router.get(
    path=EndpointRoute.ADMIN_ROUTERS + "/{router_id}",
    dependencies=[Security(dependency=get_current_key)],
    status_code=200,
    responses=get_documentation_responses([RouterNotFoundHTTPException, NotAdminUserHTTPException]),
)
async def get_router(
    router_id: int = Path(description="The router ID."),
    get_one_router_use_case: GetOneRouterUseCase = Depends(get_one_router_use_case_factory),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> Router:
    command = GetOneRouterCommand(
        router_id=router_id,
        user_id=request_context.get().user_id,
    )
    try:
        result = await get_one_router_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing get_router use case",
            extra={
                "user_id": command.user_id,
                "router_id": command.router_id,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()
    match result:
        case GetOneRouterUseCaseSuccess(returned_router):
            return Router.model_validate(returned_router, from_attributes=True)
        case RouterNotFoundError(router_id=not_found_id):
            raise RouterNotFoundHTTPException(not_found_id)
        case UserIsNotAdminError():
            raise NotAdminUserHTTPException()


@router.get(
    path=EndpointRoute.ADMIN_ROUTERS,
    dependencies=[Security(dependency=get_current_key)],
    status_code=200,
    responses=get_documentation_responses([NotAdminUserHTTPException]),
)
async def get_routers(
    offset: int = Query(default=0, ge=0, description="Number of routers to skip."),
    limit: int = Query(default=10, ge=1, le=100, description="Maximum number of routers to return."),
    sort_by: RouterSortField = Query(default=RouterSortField.ID, description="Field to sort by."),
    sort_order: SortOrder = Query(default=SortOrder.ASC, description="Sort order."),
    get_routers_use_case: GetRoutersUseCase = Depends(get_routers_use_case_factory),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> Routers:
    command = GetRoutersCommand(
        user_id=request_context.get().user_id,
        offset=offset,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    try:
        result = await get_routers_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing get_routers use case",
            extra={
                "user_id": command.user_id,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()
    match result:
        case GetRoutersUseCaseSuccess(routers, total):
            return Routers(
                total=total,
                offset=offset,
                limit=limit,
                data=[Router.model_validate(r, from_attributes=True) for r in routers],
            )
        case UserIsNotAdminError():
            raise NotAdminUserHTTPException()


@router.delete(
    path=EndpointRoute.ADMIN_ROUTERS + "/{router_id}",
    dependencies=[Security(dependency=get_current_key)],
    responses=get_documentation_responses([RouterNotFoundHTTPException, NotAdminUserHTTPException]),
    status_code=200,
)
async def delete_router(
    router_id: int = Path(description="The ID of the router to delete (router ID, eg. 123)."),
    delete_router_use_case: DeleteRouterUseCase = Depends(delete_router_use_case_factory),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> Router:
    command = DeleteRouterCommand(
        user_id=request_context.get().user_id,
        router_id=router_id,
    )
    try:
        result = await delete_router_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing delete_router use case",
            extra={
                "user_id": command.user_id,
                "router_id": command.router_id,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()

    match result:
        case DeleteRouterUseCaseSuccess(deleted_router):
            return Router.model_validate(deleted_router, from_attributes=True)
        case RouterNotFoundError(router_id=not_found_id):
            raise RouterNotFoundHTTPException(not_found_id)
        case UserIsNotAdminError():
            raise NotAdminUserHTTPException()
