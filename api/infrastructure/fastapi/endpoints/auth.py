import logging

from fastapi import APIRouter, Depends, Request

from api.dependencies import auth_login_use_case_factory, auth_sso_login_use_case_factory
from api.domain.auth.errors import InvalidOidcTokenError, SsoProviderNotAvailableError
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
from api.infrastructure.fastapi.schemas.auth import AuthLoginBody, AuthLoginResponse, AuthSsoLoginBody
from api.use_cases.auth import (
    AuthLoginCommand,
    AuthLoginUseCase,
    AuthLoginUseCaseSuccess,
    AuthSsoLoginCommand,
    AuthSsoLoginUseCase,
    AuthSsoLoginUseCaseSuccess,
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
    path=EndpointRoute.AUTH_SSO_LOGIN,
    status_code=200,
    response_model=AuthLoginResponse,
    responses=get_documentation_responses(
        [InvalidPasswordHTTPException, UserNotFoundHTTPException, RoleNotFoundHTTPException], add_auth_exceptions=False
    ),
)
async def sso_login(
    request: Request,
    body: AuthSsoLoginBody,
    auth_sso_login_use_case: AuthSsoLoginUseCase = Depends(auth_sso_login_use_case_factory),
):
    session_cookie = request.headers.get("cookie")
    if not session_cookie:
        raise InvalidOidcTokenHTTPException()

    command = AuthSsoLoginCommand(
        session_cookie=session_cookie,
        name=body.name,
        organization=body.organization,
        sub=body.sub,
        iss=body.iss,
        expires=body.expires,
    )
    try:
        result = await auth_sso_login_use_case.execute(command=command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing auth oidc login use case",
            extra={
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()

    match result:
        case AuthSsoLoginUseCaseSuccess(key=key):
            return AuthLoginResponse.model_validate(key, from_attributes=True)
        case InvalidOidcTokenError():
            raise InvalidOidcTokenHTTPException()
        case SsoProviderNotAvailableError():
            raise OidcProviderNotAvailableHTTPException()
        case RoleNotFoundError(id=role_id):
            raise RoleNotFoundHTTPException(role_id=role_id)
