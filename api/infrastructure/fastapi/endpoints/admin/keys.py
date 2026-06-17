from contextvars import ContextVar
import logging

from fastapi import Body, Depends, Security

from api.dependencies import create_key_use_case_factory
from api.domain.user.errors import UserNotFoundError
from api.infrastructure.fastapi import AccessController
from api.infrastructure.fastapi.context import RequestContext
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.admin import router
from api.infrastructure.fastapi.endpoints.exceptions import (
    InternalServerHTTPException,
    NotAdminUserHTTPException,
    UserNotFoundHTTPException,
)
from api.infrastructure.fastapi.schemas.admin.keys import CreateKeyBody, CreateKeyResponse
from api.use_cases.admin.keys import CreateKeyCommand, CreateKeyUseCase, CreateKeyUseCaseSuccess
from api.utils.dependencies import get_request_context
from api.utils.variables import EndpointRoute

logger = logging.getLogger(__name__)


@router.post(
    path=EndpointRoute.ADMIN_KEYS,
    dependencies=[Security(dependency=AccessController(only_admin=True))],
    status_code=201,
    responses=get_documentation_responses([NotAdminUserHTTPException, UserNotFoundHTTPException]),
)
async def create_key(
    body: CreateKeyBody = Body(description="The key creation request."),
    create_key_use_case: CreateKeyUseCase = Depends(create_key_use_case_factory),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> CreateKeyResponse:
    """
    Create a new key for a user.
    """

    command = CreateKeyCommand(user_id=body.user, name=body.name, expire=body.expires)
    try:
        result = await create_key_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing create_key use case",
            extra={
                "authenticated_user_id": request_context.get().user.id,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()

    match result:
        case CreateKeyUseCaseSuccess(key=key):
            return CreateKeyResponse.model_validate(key, from_attributes=True)
        case UserNotFoundError(id=user_id):
            raise UserNotFoundHTTPException(user_id)
