import logging

from fastapi import Depends, Path, Security

from api.dependencies import delete_organization_use_case_factory
from api.domain.organization.errors import OrganizationHasUsersError, OrganizationNotFoundError
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.fastapi.accesscontroller import AccessController
from api.infrastructure.fastapi.dependencies import get_authenticated_user
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.admin import router
from api.infrastructure.fastapi.endpoints.exceptions import (
    InternalServerHTTPException,
    NotAdminUserHTTPException,
    OrganizationHasUsersHTTPException,
    OrganizationNotFoundHTTPException,
)
from api.infrastructure.fastapi.schemas.admin.organizations import OrganizationResponse
from api.use_cases.admin.organizations import (
    DeleteOrganizationCommand,
    DeleteOrganizationUseCase,
    DeleteOrganizationUseCaseSuccess,
)
from api.utils.variables import EndpointRoute

logger = logging.getLogger(__name__)


@router.delete(
    path=EndpointRoute.ADMIN_ORGANIZATIONS + "/{organization_id}",
    dependencies=[Security(dependency=AccessController(only_admin=True))],
    status_code=200,
    responses=get_documentation_responses([NotAdminUserHTTPException, OrganizationNotFoundHTTPException, OrganizationHasUsersHTTPException]),
)
async def delete_organization(
    organization_id: int = Path(description="The ID of the organization to delete."),
    delete_organization_use_case: DeleteOrganizationUseCase = Depends(delete_organization_use_case_factory),
    authenticated_user: AuthenticatedUserView = Depends(get_authenticated_user),
) -> OrganizationResponse:
    try:
        command = DeleteOrganizationCommand(organization_id=organization_id)
        result = await delete_organization_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing delete_organization use case",
            extra={
                "authenticated_user_id": authenticated_user.id,
                "organization_id": organization_id,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()

    match result:
        case DeleteOrganizationUseCaseSuccess(organization=organization):
            return OrganizationResponse.model_validate(organization)
        case OrganizationNotFoundError(id=organization_id):
            raise OrganizationNotFoundHTTPException(organization_id)
        case OrganizationHasUsersError(id=organization_id, number_of_users=number_of_users):
            raise OrganizationHasUsersHTTPException(organization_id=organization_id, number_of_users=number_of_users)
