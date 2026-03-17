from contextvars import ContextVar
import logging

from fastapi import Body, Depends, Security

from api.dependencies import create_user_use_case_factory, get_request_context
from api.domain.user.errors import OrganizationNotFoundError, RoleNotFoundError, UserAlreadyExistsError
from api.domain.userinfo.errors import UserIsNotAdminError
from api.infrastructure.fastapi.access import get_current_key
from api.infrastructure.fastapi.context import RequestContext
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.admin import router
from api.infrastructure.fastapi.endpoints.exceptions import (
    InternalServerHTTPException,
    NotAdminUserHTTPException,
    OrganizationNotFoundHTTPException,
    RoleNotFoundHTTPException,
    UserAlreadyExistsHTTPException,
)
from api.infrastructure.fastapi.schemas.users import CreateUserBody, UserResponse
from api.use_cases.admin.users import CreateUserCommand, CreateUserUseCase, CreateUserUseCaseSuccess
from api.utils.variables import EndpointRoute

logger = logging.getLogger(__name__)


@router.post(
    path=EndpointRoute.ADMIN_USERS,
    dependencies=[Security(dependency=get_current_key)],
    status_code=201,
    responses=get_documentation_responses(
        [UserAlreadyExistsHTTPException, RoleNotFoundHTTPException, OrganizationNotFoundHTTPException, NotAdminUserHTTPException]
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
        case RoleNotFoundError(role_id=role_id):
            raise RoleNotFoundHTTPException(role_id)
        case OrganizationNotFoundError(organization_id=organization_id):
            raise OrganizationNotFoundHTTPException(organization_id)
        case UserIsNotAdminError():
            raise NotAdminUserHTTPException()
