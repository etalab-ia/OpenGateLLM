import logging

from fastapi import APIRouter, Depends, Security

from api.dependencies import get_me_use_case_factory
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.fastapi.accesscontroller import AccessController
from api.infrastructure.fastapi.dependencies import get_authenticated_user
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.exceptions import InternalServerHTTPException
from api.infrastructure.fastapi.schemas.me import MeResponse
from api.use_cases.me import GetMeCommand, GetMeUseCase, GetMeUseCaseSuccess
from api.utils.variables import EndpointRoute, RouterName

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=[RouterName.ME.title()])


@router.get(
    path=f"{EndpointRoute.ME}/info",
    dependencies=[Security(dependency=AccessController(allow_expired=True))],
    status_code=200,
    responses=get_documentation_responses([]),
    deprecated=True,
)
@router.get(
    path=EndpointRoute.ME,
    dependencies=[Security(dependency=AccessController(allow_expired=True))],
    status_code=200,
    responses=get_documentation_responses([]),
)
async def get_me(
    get_me_use_case: GetMeUseCase = Depends(get_me_use_case_factory),
    authenticated_user: AuthenticatedUserView = Depends(get_authenticated_user),
) -> MeResponse:
    """
    Get my user information.
    """
    command = GetMeCommand(authenticated_user=authenticated_user)
    try:
        result = await get_me_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing get_me use case",
            extra={
                "authenticated_user_id": authenticated_user.id,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()

    match result:
        case GetMeUseCaseSuccess(authenticated_user=user):
            return MeResponse.model_validate(user, from_attributes=True)
