import logging

from fastapi import APIRouter, Depends

from api.dependencies import auth_login_use_case_factory
from api.domain.user.errors import InvalidUserPasswordError, UserNotFoundError
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.exceptions import InternalServerHTTPException, InvalidPasswordHTTPException, UserNotFoundHTTPException
from api.infrastructure.fastapi.schemas.auth import AuthLoginBody, AuthLoginResponse
from api.use_cases.auth import AuthLoginCommand, AuthLoginUseCase, AuthLoginUseCaseSuccess
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
