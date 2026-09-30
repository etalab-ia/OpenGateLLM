from fastapi import Body, Depends, Path, Query, Security

from api.dependencies import (
    create_role_use_case_factory,
    delete_role_use_case_factory,
    get_one_role_use_case_factory,
    get_roles_use_case_factory,
    update_role_use_case_factory,
)
from api.domain import SortField, SortOrder
from api.domain.role.entities import Limit
from api.domain.role.errors import RoleAlreadyExistsError, RoleHasUsersError, RoleNotFoundError
from api.infrastructure.fastapi.accesscontroller import AccessController
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.admin import router
from api.infrastructure.fastapi.endpoints.exceptions import (
    NotAdminUserHTTPException,
    RoleAlreadyExistsHTTPException,
    RoleHasUsersHTTPException,
    RoleNotFoundHTTPException,
)
from api.infrastructure.fastapi.routes import EndpointRoute
from api.infrastructure.fastapi.schemas.admin.roles import CreateRoleBody, RoleResponse, RolesResponse, UpdateRoleBody
from api.use_cases.admin.roles import (
    CreateRoleCommand,
    CreateRoleUseCase,
    CreateRoleUseCaseSuccess,
    DeleteRoleCommand,
    DeleteRoleUseCase,
    DeleteRoleUseCaseSuccess,
    GetOneRoleCommand,
    GetOneRoleUseCase,
    GetOneRoleUseCaseSuccess,
    GetRolesCommand,
    GetRolesUseCase,
    GetRolesUseCaseSuccess,
    UpdateRoleCommand,
    UpdateRoleUseCase,
    UpdateRoleUseCaseSuccess,
)


@router.post(
    path=EndpointRoute.ADMIN_ROLES,
    dependencies=[Security(dependency=AccessController(only_admin=True))],
    status_code=201,
    responses=get_documentation_responses([NotAdminUserHTTPException, RoleAlreadyExistsHTTPException]),
)
async def create_role(
    body: CreateRoleBody = Body(description="The role creation request."),
    create_role_use_case: CreateRoleUseCase = Depends(create_role_use_case_factory),
) -> RoleResponse:
    command = CreateRoleCommand(name=body.name, permissions=body.permissions, limits=body.limits)
    result = await create_role_use_case.execute(command)

    match result:
        case CreateRoleUseCaseSuccess(role=role):
            return RoleResponse.model_validate(role, from_attributes=True)
        case RoleAlreadyExistsError(name=name):
            raise RoleAlreadyExistsHTTPException(name)


@router.patch(
    path=EndpointRoute.ADMIN_ROLES + "/{role_id}",
    dependencies=[Security(dependency=AccessController(only_admin=True))],
    status_code=200,
    responses=get_documentation_responses([NotAdminUserHTTPException, RoleAlreadyExistsHTTPException, RoleNotFoundHTTPException]),
)
async def update_role(
    role_id: int = Path(description="The ID of the role to update."),
    body: UpdateRoleBody = Body(description="The role update request."),
    update_role_use_case: UpdateRoleUseCase = Depends(update_role_use_case_factory),
) -> RoleResponse:
    command = UpdateRoleCommand(
        role_id=role_id,
        name=body.name,
        permissions=body.permissions,
        limits=[Limit(router_id=body_limit.router_id, type=body_limit.type, value=body_limit.value) for body_limit in body.limits],
    )
    result = await update_role_use_case.execute(command)

    match result:
        case UpdateRoleUseCaseSuccess(role=role):
            return RoleResponse.model_validate(role, from_attributes=True)
        case RoleNotFoundError(id=not_found_role_id):
            raise RoleNotFoundHTTPException(not_found_role_id)
        case RoleAlreadyExistsError(name=name):
            raise RoleAlreadyExistsHTTPException(name)


@router.get(
    path=EndpointRoute.ADMIN_ROLES,
    dependencies=[Security(dependency=AccessController(only_admin=True))],
    status_code=200,
    responses=get_documentation_responses([NotAdminUserHTTPException]),
)
async def get_roles(
    offset: int = Query(default=0, ge=0, description="Number of roles to skip."),
    limit: int = Query(default=10, ge=1, le=100, description="Maximum number of roles to return."),
    sort_by: SortField = Query(default=SortField.ID, description="Field to sort by."),
    sort_order: SortOrder = Query(default=SortOrder.ASC, description="Sort order."),
    get_roles_use_case: GetRolesUseCase = Depends(get_roles_use_case_factory),
) -> RolesResponse:
    command = GetRolesCommand(offset=offset, limit=limit, sort_by=sort_by, sort_order=sort_order)
    result = await get_roles_use_case.execute(command)
    match result:
        case GetRolesUseCaseSuccess(role_page=roles_page):
            return RolesResponse(
                total=roles_page.total,
                offset=offset,
                limit=limit,
                data=[RoleResponse.model_validate(role, from_attributes=True) for role in roles_page.data],
            )


@router.get(
    path=EndpointRoute.ADMIN_ROLES + "/{role_id}",
    dependencies=[Security(dependency=AccessController(only_admin=True))],
    status_code=200,
    responses=get_documentation_responses([NotAdminUserHTTPException, RoleNotFoundHTTPException]),
)
async def get_role(
    role_id: int = Path(description="The ID of the role to get."),
    get_one_role_use_case: GetOneRoleUseCase = Depends(get_one_role_use_case_factory),
) -> RoleResponse:
    command = GetOneRoleCommand(role_id=role_id)
    result = await get_one_role_use_case.execute(command)

    match result:
        case GetOneRoleUseCaseSuccess(role=role):
            return RoleResponse.model_validate(role, from_attributes=True)
        case RoleNotFoundError(id=role_id):
            raise RoleNotFoundHTTPException(role_id)


@router.delete(
    path=EndpointRoute.ADMIN_ROLES + "/{role_id}",
    dependencies=[Security(dependency=AccessController(only_admin=True))],
    status_code=200,
    responses=get_documentation_responses([NotAdminUserHTTPException, RoleNotFoundHTTPException, RoleHasUsersHTTPException]),
)
async def delete_role(
    role_id: int = Path(description="The ID of the role to delete."),
    delete_role_use_case: DeleteRoleUseCase = Depends(delete_role_use_case_factory),
) -> RoleResponse:
    command = DeleteRoleCommand(role_id=role_id)
    result = await delete_role_use_case.execute(command)

    match result:
        case DeleteRoleUseCaseSuccess(role=role):
            return RoleResponse.model_validate(role, from_attributes=True)
        case RoleNotFoundError(id=role_id):
            raise RoleNotFoundHTTPException(role_id)
        case RoleHasUsersError(id=role_id):
            raise RoleHasUsersHTTPException(role_id=role_id)
