from fastapi import Body, Depends, Path, Query, Security

from api.dependencies import (
    create_router_use_case_factory,
    delete_router_use_case_factory,
    get_one_router_use_case_factory,
    get_routers_use_case_factory,
    update_router_use_case_factory,
)
from api.domain import SortField, SortOrder
from api.domain.router.errors import (
    RouterAliasAlreadyExistsError,
    RouterNameAlreadyExistsError,
    RouterNotFoundError,
    UserCannotCreateRouterError,
    UserCannotDeleteRouterError,
    UserCannotReadRouterError,
    UserCannotUpdateRouterError,
)
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.fastapi.accesscontroller import AccessController
from api.infrastructure.fastapi.dependencies import get_authenticated_user
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.admin import router
from api.infrastructure.fastapi.endpoints.exceptions import (
    RouterAliasAlreadyExistsHTTPException,
    RouterAlreadyExistsHTTPException,
    RouterNotFoundHTTPException,
    UnauthorizedActionHTTPException,
)
from api.infrastructure.fastapi.routes import EndpointRoute
from api.infrastructure.fastapi.schemas.admin.routers import CreateRouterBody, RouterResponse, RoutersResponse, UpdateRouterBody
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
    UpdateRouterCommand,
    UpdateRouterUseCase,
    UpdateRouterUseCaseSuccess,
)


@router.post(
    path=EndpointRoute.ADMIN_ROUTERS,
    dependencies=[Security(dependency=AccessController())],
    status_code=201,
    responses=get_documentation_responses([RouterAliasAlreadyExistsHTTPException, RouterAlreadyExistsHTTPException, UnauthorizedActionHTTPException]),
)
async def create_router(
    body: CreateRouterBody = Body(description="The router creation request."),
    create_router_use_case: CreateRouterUseCase = Depends(create_router_use_case_factory),
    authenticated_user: AuthenticatedUserView = Depends(get_authenticated_user),
) -> RouterResponse:
    command = CreateRouterCommand(
        user_id=authenticated_user.id,
        name=body.name,
        router_type=body.router_type,
        aliases=body.aliases,
        qos_retries_before_reject=body.qos_retries_before_reject,
        cost_prompt_tokens=body.cost_prompt_tokens,
        cost_completion_tokens=body.cost_completion_tokens,
    )
    result = await create_router_use_case.execute(command)

    match result:
        case CreateRouterUseCaseSuccess(created_router):
            return RouterResponse.model_validate(created_router, from_attributes=True)
        case RouterAliasAlreadyExistsError(name):
            raise RouterAliasAlreadyExistsHTTPException(name)
        case RouterNameAlreadyExistsError(name):
            raise RouterAlreadyExistsHTTPException(name)
        case UserCannotCreateRouterError(user_id=user_id):
            raise UnauthorizedActionHTTPException(user_id)


@router.get(
    path=EndpointRoute.ADMIN_ROUTERS + "/{router_id}",
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    responses=get_documentation_responses([UnauthorizedActionHTTPException, RouterNotFoundHTTPException]),
)
async def get_router(
    router_id: int = Path(description="The router ID."),
    get_one_router_use_case: GetOneRouterUseCase = Depends(get_one_router_use_case_factory),
    authenticated_user: AuthenticatedUserView = Depends(get_authenticated_user),
) -> RouterResponse:
    command = GetOneRouterCommand(authenticated_user_id=authenticated_user.id, router_id=router_id)
    result = await get_one_router_use_case.execute(command)
    match result:
        case GetOneRouterUseCaseSuccess(returned_router):
            return RouterResponse.model_validate(returned_router, from_attributes=True)
        case RouterNotFoundError(id=not_found_id):
            raise RouterNotFoundHTTPException(router_id=not_found_id)
        case UserCannotReadRouterError(user_id=authenticated_user_id):
            raise UnauthorizedActionHTTPException(authenticated_user_id)


@router.get(
    path=EndpointRoute.ADMIN_ROUTERS,
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    responses=get_documentation_responses([UnauthorizedActionHTTPException]),
)
async def get_routers(
    offset: int = Query(default=0, ge=0, description="Number of routers to skip."),
    limit: int = Query(default=10, ge=1, le=100, description="Maximum number of routers to return."),
    sort_by: SortField = Query(default=SortField.ID, description="Field to sort by."),
    sort_order: SortOrder = Query(default=SortOrder.ASC, description="Sort order."),
    get_routers_use_case: GetRoutersUseCase = Depends(get_routers_use_case_factory),
    authenticated_user: AuthenticatedUserView = Depends(get_authenticated_user),
) -> RoutersResponse:
    command = GetRoutersCommand(
        authenticated_user_id=authenticated_user.id,
        offset=offset,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    result = await get_routers_use_case.execute(command)
    match result:
        case GetRoutersUseCaseSuccess(router_page=router_page):
            return RoutersResponse(
                total=router_page.total,
                offset=offset,
                limit=limit,
                data=[RouterResponse.model_validate(r, from_attributes=True) for r in router_page.data],
            )
        case UserCannotReadRouterError(user_id=authenticated_user_id):
            raise UnauthorizedActionHTTPException(authenticated_user_id)


@router.delete(
    path=EndpointRoute.ADMIN_ROUTERS + "/{router_id}",
    dependencies=[Security(dependency=AccessController())],
    responses=get_documentation_responses([UnauthorizedActionHTTPException, RouterNotFoundHTTPException]),
    status_code=200,
)
async def delete_router(
    router_id: int = Path(description="The ID of the router to delete (router ID, eg. 123)."),
    delete_router_use_case: DeleteRouterUseCase = Depends(delete_router_use_case_factory),
    authenticated_user: AuthenticatedUserView = Depends(get_authenticated_user),
) -> RouterResponse:
    command = DeleteRouterCommand(authenticated_user_id=authenticated_user.id, router_id=router_id)
    result = await delete_router_use_case.execute(command)

    match result:
        case DeleteRouterUseCaseSuccess(deleted_router):
            return RouterResponse.model_validate(deleted_router, from_attributes=True)
        case RouterNotFoundError(id=not_found_id):
            raise RouterNotFoundHTTPException(not_found_id)
        case UserCannotDeleteRouterError(user_id=user_id):
            raise UnauthorizedActionHTTPException(user_id)


@router.patch(
    path=EndpointRoute.ADMIN_ROUTERS + "/{router_id}",
    dependencies=[Security(dependency=AccessController())],
    responses=get_documentation_responses(
        [
            UnauthorizedActionHTTPException,
            RouterNotFoundHTTPException,
            RouterAliasAlreadyExistsHTTPException,
            RouterAlreadyExistsHTTPException,
        ]
    ),
    status_code=200,
)
async def update_router(
    router_id: int = Path(description="The ID of the router to update (router ID, eg. 123)."),
    update_router_use_case: UpdateRouterUseCase = Depends(update_router_use_case_factory),
    authenticated_user: AuthenticatedUserView = Depends(get_authenticated_user),
    body: UpdateRouterBody = Body(description="The router update request."),
) -> RouterResponse:
    command = UpdateRouterCommand(
        authenticated_user_id=authenticated_user.id,
        router_id=router_id,
        name=body.name,
        router_type=body.router_type,
        aliases=body.aliases,
        qos_retries_before_reject=body.qos_retries_before_reject,
        cost_prompt_tokens=body.cost_prompt_tokens,
        cost_completion_tokens=body.cost_completion_tokens,
    )
    result = await update_router_use_case.execute(command)
    match result:
        case UpdateRouterUseCaseSuccess(router=updated_router):
            return RouterResponse.model_validate(updated_router, from_attributes=True)
        case RouterNotFoundError(id=not_found_id):
            raise RouterNotFoundHTTPException(not_found_id)
        case RouterAliasAlreadyExistsError(aliases):
            raise RouterAliasAlreadyExistsHTTPException(aliases)
        case RouterNameAlreadyExistsError(name):
            raise RouterAlreadyExistsHTTPException(name)
        case UserCannotUpdateRouterError(user_id=user_id):
            raise UnauthorizedActionHTTPException(user_id)
