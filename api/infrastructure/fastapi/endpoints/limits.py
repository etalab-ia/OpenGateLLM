from fastapi import APIRouter, Depends, Security

from api.dependencies import get_limits_use_case_factory
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.fastapi.accesscontroller import AccessController
from api.infrastructure.fastapi.dependencies import get_authenticated_user
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.routes import EndpointRoute, RouterName
from api.infrastructure.fastapi.schemas.limits import LimitResponse, LimitsResponse
from api.use_cases.limits import GetLimitsCommand, GetLimitsUseCase, GetLimitsUseCaseSuccess

router = APIRouter(prefix="/v1", tags=[RouterName.LIMITS.title()])


@router.get(
    path=EndpointRoute.LIMITS,
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    responses=get_documentation_responses([]),
)
async def get_limits(
    get_limits_use_case: GetLimitsUseCase = Depends(get_limits_use_case_factory),
    authenticated_user: AuthenticatedUserView = Depends(get_authenticated_user),
) -> LimitsResponse:
    """
    Get my rate limits on each model I am allowed to use.
    """
    command = GetLimitsCommand(authenticated_user=authenticated_user)
    result = await get_limits_use_case.execute(command)

    match result:
        case GetLimitsUseCaseSuccess(limits=limits):
            return LimitsResponse(data=[LimitResponse.model_validate(limit, from_attributes=True) for limit in limits])
