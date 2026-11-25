from fastapi import APIRouter, Depends, Security

from api.dependencies import get_my_organization_use_case_factory
from api.domain.organization.errors import OrganizationNotFoundError, UserCannotReadOrganizationError
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.fastapi.accesscontroller import AccessController
from api.infrastructure.fastapi.dependencies import get_authenticated_user
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.exceptions import OrganizationNotFoundHTTPException, UnauthorizedActionHTTPException
from api.infrastructure.fastapi.routes import EndpointRoute, RouterName
from api.infrastructure.fastapi.schemas.admin.organizations import OrganizationResponse
from api.use_cases.organizations import GetMyOrganizationCommand, GetMyOrganizationUseCase, GetMyOrganizationUseCaseSuccess

router = APIRouter(prefix="/v1", tags=[RouterName.ORGANIZATIONS.title()])


@router.get(
    path=EndpointRoute.ORGANIZATIONS_ME,
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    responses=get_documentation_responses([OrganizationNotFoundHTTPException, UnauthorizedActionHTTPException]),
)
async def get_my_organization(
    get_my_organization_use_case: GetMyOrganizationUseCase = Depends(get_my_organization_use_case_factory),
    authenticated_user: AuthenticatedUserView = Depends(get_authenticated_user),
) -> OrganizationResponse:
    """
    Get the organization of the authenticated user.
    """

    command = GetMyOrganizationCommand(authenticated_user_id=authenticated_user.id, organization_id=authenticated_user.organization_id)
    result = await get_my_organization_use_case.execute(command)

    match result:
        case GetMyOrganizationUseCaseSuccess(organization=organization):
            return OrganizationResponse.model_validate(organization, from_attributes=True)
        case OrganizationNotFoundError(id=not_found_organization_id):
            raise OrganizationNotFoundHTTPException(not_found_organization_id)
        case UserCannotReadOrganizationError(user_id=user_id):
            raise UnauthorizedActionHTTPException(user_id)
