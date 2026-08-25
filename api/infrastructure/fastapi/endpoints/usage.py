import logging

from fastapi import APIRouter, Depends, Query, Security

from api.dependencies import get_usages_use_case_factory
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.fastapi.accesscontroller import AccessController
from api.infrastructure.fastapi.dependencies import get_authenticated_user
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.exceptions import InternalServerHTTPException
from api.infrastructure.fastapi.schemas.usage import EndpointUsage, UsageResponse, UsagesResponse
from api.use_cases.usage import GetUsagesCommand, GetUsagesUseCase, GetUsagesUseCaseSuccess
from api.utils.variables import EndpointRoute, RouterName

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=[RouterName.USAGE.title()])


@router.get(
    path=EndpointRoute.ME_USAGE,
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    responses=get_documentation_responses([]),
    deprecated=True,
)
@router.get(
    path=EndpointRoute.USAGE,
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    responses=get_documentation_responses([]),
)
async def get_usages(
    offset: int = Query(default=0, ge=0, description="Number of usages to skip."),
    limit: int = Query(default=10, ge=1, le=100, description="Maximum number of usages to return."),
    start_time: int | None = Query(default=None, description="Start time as Unix timestamp (if not provided, will be set to 30 days ago)."),
    end_time: int | None = Query(default=None, description="End time as Unix timestamp (if not provided, will be set to now)."),
    endpoint: EndpointUsage | None = Query(default=None, description="The endpoint to get usage for."),
    get_usages_use_case: GetUsagesUseCase = Depends(get_usages_use_case_factory),
    authenticated_user: AuthenticatedUserView = Depends(get_authenticated_user),
) -> UsagesResponse:
    """
    Get usage for the current user.
    """

    command = GetUsagesCommand(
        user_id=authenticated_user.id,
        offset=offset,
        limit=limit,
        start_time=start_time,
        end_time=end_time,
        endpoint=endpoint.value if endpoint is not None else None,
    )
    try:
        result = await get_usages_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing get_usages use case",
            extra={
                "authenticated_user_id": authenticated_user.id,
                "offset": command.offset,
                "limit": command.limit,
                "start_time": command.start_time,
                "end_time": command.end_time,
                "endpoint": command.endpoint,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()

    match result:
        case GetUsagesUseCaseSuccess(usage_page=usage_page):
            return UsagesResponse(
                total=usage_page.total,
                offset=offset,
                limit=limit,
                data=[UsageResponse.model_validate(usage, from_attributes=True) for usage in usage_page.data],
            )
