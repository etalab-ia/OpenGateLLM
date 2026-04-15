from contextvars import ContextVar
import logging

from fastapi import Body, Depends, Path, Security

from api.dependencies import create_role_use_case_factory, get_request_context, update_role_use_case_factory
from api.domain.role.entities import Limit
from api.domain.role.errors import RoleAlreadyExistsError, RoleNotFoundError
from api.domain.userinfo.errors import UserIsNotAdminError
from api.infrastructure.fastapi.access import get_current_key
from api.infrastructure.fastapi.context import RequestContext
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.admin import router
from api.infrastructure.fastapi.endpoints.exceptions import (
    InternalServerHTTPException,
    NotAdminUserHTTPException,
    RoleAlreadyExistsHTTPException,
    RoleNotFoundHTTPException,
)
from api.infrastructure.fastapi.schemas.roles import CreateRoleBody, RoleResponse
from api.use_cases.admin.roles import (
    CreateRoleCommand,
    CreateRoleUseCase,
    CreateRoleUseCaseSuccess,
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
        case RoleNotFoundError(role_id=not_found_role_id):
            raise RoleNotFoundHTTPException(not_found_role_id)
        case RoleAlreadyExistsError(name=name):
            raise RoleAlreadyExistsHTTPException(name)
        case UserIsNotAdminError():
            raise NotAdminUserHTTPException()
