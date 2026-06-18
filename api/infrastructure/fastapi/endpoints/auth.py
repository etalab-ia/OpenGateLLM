import logging

from fastapi import APIRouter, Depends

from api.dependencies import auth_login_use_case_factory, auth_oidc_login_use_case_factory
from api.domain.auth.errors import InvalidOidcTokenError, OidcProviderNotAvailableError
from api.domain.role.errors import RoleNotFoundError
from api.domain.user.errors import InvalidUserPasswordError, UserNotFoundError
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.exceptions import (
    InternalServerHTTPException,
    InvalidOidcTokenHTTPException,
    InvalidPasswordHTTPException,
    OidcProviderNotAvailableHTTPException,
    RoleNotFoundHTTPException,
    UserNotFoundHTTPException,
)
from api.infrastructure.fastapi.schemas.auth import AuthLoginBody, AuthLoginResponse, AuthOidcLoginBody
from api.use_cases.auth import (
    AuthLoginCommand,
    AuthLoginUseCase,
    AuthLoginUseCaseSuccess,
    AuthOidcLoginCommand,
    AuthOidcLoginUseCase,
    AuthOidcLoginUseCaseSuccess,
)
from api.utils.variables import EndpointRoute, RouterName

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=[RouterName.AUTH.title()])


@router.post(
    path=EndpointRoute.AUTH_LOGIN,
    status_code=200,
    response_model=AuthLoginResponse,
    responses=get_documentation_responses([InvalidPasswordHTTPException, UserNotFoundHTTPException], add_auth_exceptions=False),
)
async def login(body: AuthLoginBody, auth_login_use_case: AuthLoginUseCase = Depends(auth_login_use_case_factory)):
    command = AuthLoginCommand(email=body.email, password=body.password)
    try:
        result = await auth_login_use_case.execute(command=command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing auth login use case",
            extra={
                "email": body.email,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()

    match result:
        case AuthLoginUseCaseSuccess(key=key):
            return AuthLoginResponse.model_validate(key, from_attributes=True)
        case InvalidUserPasswordError():
            raise InvalidPasswordHTTPException()
        case UserNotFoundError(email=email):
            raise UserNotFoundHTTPException(email=email)


@router.post(
    path=EndpointRoute.AUTH_OIDC_LOGIN,
    status_code=200,
    response_model=AuthLoginResponse,
    responses=get_documentation_responses(
        [InvalidPasswordHTTPException, UserNotFoundHTTPException, RoleNotFoundHTTPException], add_auth_exceptions=False
    ),
)
async def oidc_login(body: AuthOidcLoginBody, auth_oidc_login_use_case: AuthOidcLoginUseCase = Depends(auth_oidc_login_use_case_factory)):
    command = AuthOidcLoginCommand(email=body.email, id_token=body.id_token)
    try:
        result = await auth_oidc_login_use_case.execute(command=command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing auth oidc login use case",
            extra={
                "email": body.email,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()

    match result:
        case AuthOidcLoginUseCaseSuccess(key=key):
            return AuthLoginResponse.model_validate(key, from_attributes=True)
        case InvalidOidcTokenError():
            raise InvalidOidcTokenHTTPException()
        case OidcProviderNotAvailableError():
            raise OidcProviderNotAvailableHTTPException()
        case RoleNotFoundError(role_id=role_id):
            raise RoleNotFoundHTTPException(role_id=role_id)
