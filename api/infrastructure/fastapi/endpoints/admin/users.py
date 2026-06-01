from contextvars import ContextVar
import logging
from typing import assert_never

from fastapi import Body, Depends, Path, Query, Security

from api.dependencies import (
    create_user_use_case_factory,
    delete_user_use_case_factory,
    get_one_user_use_case_factory,
    get_request_context,
    get_users_use_case_factory,
)
from api.domain import SortOrder
from api.domain.organization.errors import OrganizationNotFoundError
from api.domain.role.errors import RoleNotFoundError
from api.domain.user.entities import UserSortField
from api.domain.user.errors import (
    DeleteUserWithProvidersError,
    DeleteUserWithRoutersError,
    UserAlreadyExistsError,
    UserExpiredError,
    UserIsNotAdminError,
    UserNotFoundError,
)
from api.infrastructure.fastapi.access import get_current_key
from api.infrastructure.fastapi.context import RequestContext
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.admin import router
from api.infrastructure.fastapi.endpoints.exceptions import (
    AccountExpiredHTTPException,
    DeleteUserWithProvidersHTTPException,
    DeleteUserWithRoutersHTTPException,
    InternalServerHTTPException,
    NotAdminUserHTTPException,
    OrganizationNotFoundHTTPException,
    RoleNotFoundHTTPException,
    UserAlreadyExistsHTTPException,
    UserNotFoundHTTPException,
)
from api.infrastructure.fastapi.schemas.users import CreateUserBody, UserResponse, UsersResponse
from api.use_cases.admin.users import (
    CreateUserCommand,
    CreateUserUseCase,
    CreateUserUseCaseSuccess,
    DeleteUserCommand,
    DeleteUserUseCase,
    DeleteUserUseCaseSuccess,
    GetOneUserCommand,
    GetOneUserUseCase,
    GetOneUserUseCaseSuccess,
    GetUsersCommand,
    GetUsersUseCase,
    GetUsersUseCaseSuccess,
)
from api.utils.variables import EndpointRoute

logger = logging.getLogger(__name__)


@router.post(
    path=EndpointRoute.ADMIN_USERS,
    dependencies=[Security(dependency=get_current_key)],
    status_code=201,
    responses=get_documentation_responses(
        [
            UserAlreadyExistsHTTPException,
            RoleNotFoundHTTPException,
            OrganizationNotFoundHTTPException,
            NotAdminUserHTTPException,
        ]
    ),
)
async def create_user(
    body: CreateUserBody = Body(description="The user creation request."),
    create_user_use_case: CreateUserUseCase = Depends(create_user_use_case_factory),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> UserResponse:
    try:
        command = CreateUserCommand(
            user_id=request_context.get().user_id,
            email=body.email,
            password=body.password,
            role_id=body.role,
            name=body.name,
            organization_id=body.organization,
            budget=body.budget,
            expires=body.expires,
            priority=body.priority,
        )
        result = await create_user_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing create_user use case",
            extra={
                "user_id": request_context.get().user_id,
                "email": body.email,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()

    match result:
        case CreateUserUseCaseSuccess(user=user):
            return UserResponse.model_validate(user, from_attributes=True)
        case UserAlreadyExistsError(email=email):
            raise UserAlreadyExistsHTTPException(email)
        case RoleNotFoundError(id=role_id):
            raise RoleNotFoundHTTPException(role_id)
        case OrganizationNotFoundError(id=organization_id):
            raise OrganizationNotFoundHTTPException(organization_id)
        case UserIsNotAdminError():
            raise NotAdminUserHTTPException()
        case UserExpiredError():
            raise AccountExpiredHTTPException()


@router.get(
    path=EndpointRoute.ADMIN_USERS + "/{user_id}",
    dependencies=[Security(dependency=get_current_key)],
    status_code=200,
    responses=get_documentation_responses([UserNotFoundHTTPException]),
)
async def get_user(
    user_id: int = Path(description="The ID of the user to get."),
    get_one_user_use_case: GetOneUserUseCase = Depends(get_one_user_use_case_factory),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> UserResponse:
    command = GetOneUserCommand(authenticated_user_id=request_context.get().user_id, user_id=user_id)
    try:
        result = await get_one_user_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing get_user use case",
            extra={
                "authenticated_user_id": command.authenticated_user_id,
                "user_id": command.user_id,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()
    match result:
        case GetOneUserUseCaseSuccess(user=returned_user):
            return UserResponse.model_validate(returned_user, from_attributes=True)
        case UserNotFoundError(id=not_found_id):
            raise UserNotFoundHTTPException(user_id=not_found_id)
        case UserIsNotAdminError():
            raise NotAdminUserHTTPException()
        case UserExpiredError():
            raise AccountExpiredHTTPException()
        case _ as unreachable:
            assert_never(unreachable)


@router.get(
    path=EndpointRoute.ADMIN_USERS,
    dependencies=[Security(dependency=get_current_key)],
    status_code=200,
    responses=get_documentation_responses([]),
)
async def get_users(
    role_id: int | None = Query(default=None, description="The ID of the role to filter the users by."),
    organization_id: int | None = Query(default=None, description="The ID of the organization to filter the users by."),
    offset: int = Query(default=0, ge=0, description="Number of users to skip."),
    limit: int = Query(default=10, ge=1, le=100, description="Maximum number of users to return."),
    sort_by: UserSortField = Query(default=UserSortField.ID, description="Field to sort by."),
    sort_order: SortOrder = Query(default=SortOrder.ASC, description="Sort order."),
    get_users_use_case: GetUsersUseCase = Depends(get_users_use_case_factory),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> UsersResponse:
    command = GetUsersCommand(
        authenticated_user_id=request_context.get().user_id,
        role_id=role_id,
        organization_id=organization_id,
        offset=offset,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    try:
        result = await get_users_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing get_users use case",
            extra={
                "authenticated_user_id": command.authenticated_user_id,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()
    match result:
        case GetUsersUseCaseSuccess(user_page=user_page):
            return UsersResponse(
                total=user_page.total,
                offset=offset,
                limit=limit,
                data=[UserResponse.model_validate(r, from_attributes=True) for r in user_page.data],
            )
        case UserIsNotAdminError():
            raise NotAdminUserHTTPException()
        case UserExpiredError():
            raise AccountExpiredHTTPException()
        case _ as unreachable:
            assert_never(unreachable)


@router.delete(
    path=EndpointRoute.ADMIN_USERS + "/{user_id}",
    dependencies=[Security(dependency=get_current_key)],
    status_code=200,
    responses=get_documentation_responses(
        [
            UserNotFoundHTTPException,
            DeleteUserWithRoutersHTTPException,
            DeleteUserWithProvidersHTTPException,
        ]
    ),
)
async def delete_user(
    user_id: int = Path(description="The ID of the user to delete."),
    delete_user_use_case: DeleteUserUseCase = Depends(delete_user_use_case_factory),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> UserResponse:
    command = DeleteUserCommand(
        authenticated_user_id=request_context.get().user_id,
        user_id=user_id,
    )
    try:
        result = await delete_user_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing delete_user use case",
            extra={
                "authenticated_user_id": command.authenticated_user_id,
                "user_id": command.user_id,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()
    match result:
        case DeleteUserUseCaseSuccess(user=user):
            return UserResponse.model_validate(user, from_attributes=True)
        case UserNotFoundError(id=not_found_id):
            raise UserNotFoundHTTPException(user_id=not_found_id)
        case DeleteUserWithRoutersError(routers_ids=routers_ids):
            raise DeleteUserWithRoutersHTTPException(routers_ids=routers_ids)
        case DeleteUserWithProvidersError(providers_ids=providers_ids):
            raise DeleteUserWithProvidersHTTPException(providers_ids=providers_ids)
        case UserIsNotAdminError():
            raise NotAdminUserHTTPException()
        case UserExpiredError():
            raise AccountExpiredHTTPException()
        case _ as unreachable:
            assert_never(unreachable)
