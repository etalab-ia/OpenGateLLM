import logging

from fastapi import Depends, Security

from api.dependencies import get_user_info_use_case_factory
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.fastapi.accesscontroller import AccessController
from api.infrastructure.fastapi.dependencies import get_authenticated_user
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.exceptions import InternalServerHTTPException
from api.infrastructure.fastapi.endpoints.me import router
from api.infrastructure.fastapi.schemas.me import UserInfoResponse
from api.use_cases.me import GetUserInfoCommand, GetUserInfoUseCase, GetUserInfoUseCaseSuccess
from api.utils.variables import EndpointRoute

logger = logging.getLogger(__name__)


@router.get(
    path=EndpointRoute.ME_INFO,
    dependencies=[Security(dependency=AccessController(allow_expired=True))],
    status_code=200,
    responses=get_documentation_responses([]),
)
async def get_user_info(
    get_user_info_use_case: GetUserInfoUseCase = Depends(get_user_info_use_case_factory),
    authenticated_user: AuthenticatedUserView = Depends(get_authenticated_user),
) -> UserInfoResponse:
    """
    Get information about the current user.
    """
    command = GetUserInfoCommand(authenticated_user=authenticated_user)
    try:
        result = await get_user_info_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing get_user_info use case",
            extra={
                "authenticated_user_id": authenticated_user.id,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()

    match result:
        case GetUserInfoUseCaseSuccess(authenticated_user=user):
            return UserInfoResponse.model_validate(user, from_attributes=True)
