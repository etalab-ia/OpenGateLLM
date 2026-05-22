from contextvars import ContextVar
import logging

from fastapi import Body, Depends, Path, Query, Security

from api.dependencies import (
    create_role_use_case_factory,
    delete_role_use_case_factory,
    get_request_context,
    get_role_use_case_factory,
    get_roles_use_case_factory,
    update_role_use_case_factory,
)
from api.domain import SortField, SortOrder
from api.domain.role.entities import Limit
from api.domain.role.errors import RoleAlreadyExistsError, RoleHasUsersError, RoleNotFoundError
from api.domain.user.errors import UserExpiredError, UserIsNotAdminError
from api.infrastructure.fastapi.access import get_current_key
from api.infrastructure.fastapi.context import RequestContext
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.admin import router
from api.infrastructure.fastapi.endpoints.exceptions import (
    AccountExpiredHTTPException,
    InternalServerHTTPException,
    NotAdminUserHTTPException,
    RoleAlreadyExistsHTTPException,
    RoleHasUsersHTTPException,
    RoleNotFoundHTTPException,
)
from api.infrastructure.fastapi.schemas.roles import CreateRoleBody, RoleResponse, RolesResponse
from api.use_cases.admin.roles import (
    CreateRoleCommand,
    CreateRoleUseCase,
    CreateRoleUseCaseSuccess,
    DeleteRoleCommand,
    DeleteRoleUseCase,
    DeleteRoleUseCaseSuccess,
    GetRoleCommand,
    GetRolesCommand,
    GetRolesUseCase,
    GetRolesUseCaseSuccess,
    GetRoleUseCase,
    GetRoleUseCaseSuccess,
    UpdateRoleCommand,
    UpdateRoleUseCase,
    UpdateRoleUseCaseSuccess,
)
from api.utils.variables import EndpointRoute

logger = logging.getLogger(__name__)


@router.post(
    path=EndpointRoute.ADMIN_ROLES,
    dependencies=[Security(dependency=get_current_key)],
    status_code=201,
    responses=get_documentation_responses([NotAdminUserHTTPException, RoleAlreadyExistsHTTPException]),
)
async def create_role(
    body: CreateRoleBody = Body(description="The role creation request."),
    create_role_use_case: CreateRoleUseCase = Depends(create_role_use_case_factory),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> RoleResponse:
    try:
        command = CreateRoleCommand(
            user_id=request_context.get().user_id,
            name=body.name,
            permissions=body.permissions,
            limits=body.limits,
        )
        result = await create_role_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing create_role use case",
            extra={
                "user_id": request_context.get().user_id,
                "role_name": body.name,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()

    match result:
        case CreateRoleUseCaseSuccess(role=role):
            return RoleResponse.model_validate(role, from_attributes=True)
        case RoleAlreadyExistsError(name=name):
            raise RoleAlreadyExistsHTTPException(name)
        case UserIsNotAdminError():
            raise NotAdminUserHTTPException()
        case UserExpiredError():
            raise AccountExpiredHTTPException()


@router.patch(
    path=EndpointRoute.ADMIN_ROLES + "/{role_id}",
    dependencies=[Security(dependency=get_current_key)],
    status_code=200,
    responses=get_documentation_responses([NotAdminUserHTTPException, RoleAlreadyExistsHTTPException, RoleNotFoundHTTPException]),
)
async def update_role(
    role_id: int = Path(description="The ID of the role to update."),
    body: CreateRoleBody = Body(description="The role update request."),
    update_role_use_case: UpdateRoleUseCase = Depends(update_role_use_case_factory),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> RoleResponse:
    try:
        command = UpdateRoleCommand(
            user_id=request_context.get().user_id,
            role_id=role_id,
            name=body.name,
            permissions=body.permissions,
            limits=[Limit(router_id=body_limit.router_id, type=body_limit.type, value=body_limit.value) for body_limit in body.limits]
            if body.limits
            else None,
        )
        result = await update_role_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing update_role use case",
            extra={
                "user_id": request_context.get().user_id,
                "role_name": body.name,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()

    match result:
        case UpdateRoleUseCaseSuccess(role=role):
            return RoleResponse.model_validate(role, from_attributes=True)
        case RoleNotFoundError(id=not_found_role_id):
            raise RoleNotFoundHTTPException(not_found_role_id)
        case RoleAlreadyExistsError(name=name):
            raise RoleAlreadyExistsHTTPException(name)
        case UserIsNotAdminError():
            raise NotAdminUserHTTPException()
        case UserExpiredError():
            raise AccountExpiredHTTPException()


@router.get(
    path=EndpointRoute.ADMIN_ROLES,
    dependencies=[Security(dependency=get_current_key)],
    status_code=200,
    responses=get_documentation_responses([NotAdminUserHTTPException]),
)
async def get_roles(
    offset: int = Query(default=0, ge=0, description="Number of roles to skip."),
    limit: int = Query(default=10, ge=1, le=100, description="Maximum number of roles to return."),
    sort_by: SortField = Query(default=SortField.ID, description="Field to sort by."),
    sort_order: SortOrder = Query(default=SortOrder.ASC, description="Sort order."),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
    get_roles_use_case: GetRolesUseCase = Depends(get_roles_use_case_factory),
) -> RolesResponse:
    try:
        command = GetRolesCommand(
            user_id=request_context.get().user_id,
            offset=offset,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        result = await get_roles_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing get_roles use case",
            extra={
                "user_id": command.user_id,
                "offset": command.offset,
                "limit": command.limit,
                "sort_by": command.sort_by,
                "sort_order": command.sort_order,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()
    match result:
        case GetRolesUseCaseSuccess(role_page=roles_page):
            return RolesResponse(
                total=roles_page.total,
                offset=offset,
                limit=limit,
                data=[RoleResponse.model_validate(role, from_attributes=True) for role in roles_page.data],
            )
        case UserIsNotAdminError():
            raise NotAdminUserHTTPException()
        case UserExpiredError():
            raise AccountExpiredHTTPException()


@router.get(
    path=EndpointRoute.ADMIN_ROLES + "/{role_id}",
    dependencies=[Security(dependency=get_current_key)],
    status_code=200,
    responses=get_documentation_responses([NotAdminUserHTTPException, RoleNotFoundHTTPException]),
)
async def get_role(
    role_id: int = Path(description="The ID of the role to get."),
    get_role_use_case: GetRoleUseCase = Depends(get_role_use_case_factory),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> RoleResponse:
    try:
        command = GetRoleCommand(
            user_id=request_context.get().user_id,
            role_id=role_id,
        )
        result = await get_role_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing get_role use case",
            extra={
                "user_id": request_context.get().user_id,
                "role_id": role_id,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()

    match result:
        case GetRoleUseCaseSuccess(role=role):
            return RoleResponse.model_validate(role, from_attributes=True)
        case RoleNotFoundError(id=role_id):
            raise RoleNotFoundHTTPException(role_id)
        case UserIsNotAdminError():
            raise NotAdminUserHTTPException()
        case UserExpiredError():
            raise AccountExpiredHTTPException()


@router.delete(
    path=EndpointRoute.ADMIN_ROLES + "/{role_id}",
    dependencies=[Security(dependency=get_current_key)],
    status_code=200,
    responses=get_documentation_responses([NotAdminUserHTTPException, RoleNotFoundHTTPException, RoleHasUsersHTTPException]),
)
async def delete_role(
    role_id: int = Path(description="The ID of the role to delete."),
    delete_role_use_case: DeleteRoleUseCase = Depends(delete_role_use_case_factory),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> RoleResponse:
    try:
        command = DeleteRoleCommand(
            user_id=request_context.get().user_id,
            role_id=role_id,
        )
        result = await delete_role_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing delete_role use case",
            extra={
                "user_id": request_context.get().user_id,
                "role_id": role_id,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()

    match result:
        case DeleteRoleUseCaseSuccess(role=role):
            return RoleResponse.model_validate(role, from_attributes=True)
        case RoleNotFoundError(id=role_id):
            raise RoleNotFoundHTTPException(role_id)
        case RoleHasUsersError(id=role_id, number_of_users=number_of_users):
            raise RoleHasUsersHTTPException(role_id=role_id, number_of_users=number_of_users)
        case UserIsNotAdminError():
            raise NotAdminUserHTTPException()
        case UserExpiredError():
            raise AccountExpiredHTTPException()
