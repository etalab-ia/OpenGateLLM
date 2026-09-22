import logging

from fastapi import APIRouter, Depends, Security

from api.dependencies import get_one_organization_use_case_factory
from api.domain.organization.errors import OrganizationNotFoundError
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.fastapi.accesscontroller import AccessController
from api.infrastructure.fastapi.dependencies import get_authenticated_user
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.exceptions import InternalServerHTTPException, OrganizationNotFoundHTTPException
from api.infrastructure.fastapi.routes import EndpointRoute, RouterName
from api.infrastructure.fastapi.schemas.admin.organizations import OrganizationResponse
from api.use_cases.admin.organizations import GetOneOrganizationCommand, GetOneOrganizationUseCase, GetOneOrganizationUseCaseSuccess

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=[RouterName.ORGANIZATIONS.title()])


@router.get(
    path=EndpointRoute.ORGANIZATIONS_ME,
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    responses=get_documentation_responses([OrganizationNotFoundHTTPException]),
)
async def get_my_organization(
    get_one_organization_use_case: GetOneOrganizationUseCase = Depends(get_one_organization_use_case_factory),
    authenticated_user: AuthenticatedUserView = Depends(get_authenticated_user),
) -> OrganizationResponse:
    """
    Get the organization of the authenticated user.
    """

    command = GetOneOrganizationCommand(organization_id=authenticated_user.organization_id)
    try:
        result = await get_one_organization_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing get_my_organization use case",
            extra={
                "authenticated_user_id": authenticated_user.id,
                "organization_id": authenticated_user.organization_id,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()

    match result:
        case GetOneOrganizationUseCaseSuccess(organization=organization):
            return OrganizationResponse.model_validate(organization, from_attributes=True)
        case OrganizationNotFoundError(id=not_found_organization_id):
            raise OrganizationNotFoundHTTPException(not_found_organization_id)
