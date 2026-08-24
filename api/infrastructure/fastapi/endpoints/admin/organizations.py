import logging

from fastapi import Body, Depends, Security

from api.dependencies import create_organization_use_case_factory
from api.domain.organization.errors import OrganizationAlreadyExistsError
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.fastapi.accesscontroller import AccessController
from api.infrastructure.fastapi.dependencies import get_authenticated_user
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.admin import router
from api.infrastructure.fastapi.endpoints.exceptions import (
    InternalServerHTTPException,
    NotAdminUserHTTPException,
    OrganizationAlreadyExistsHTTPException,
)
from api.infrastructure.fastapi.schemas.admin.organizations import CreateOrganizationBody, OrganizationResponse
from api.use_cases.admin.organizations import CreateOrganizationCommand, CreateOrganizationUseCase, CreateOrganizationUseCaseSuccess
from api.utils.variables import EndpointRoute

logger = logging.getLogger(__name__)


@router.post(
    path=EndpointRoute.ADMIN_ORGANIZATIONS,
    dependencies=[Security(dependency=AccessController(only_admin=True))],
    status_code=201,
    responses=get_documentation_responses([NotAdminUserHTTPException, OrganizationAlreadyExistsHTTPException]),
)
async def create_organization(
    body: CreateOrganizationBody = Body(description="The organization creation request."),
    create_organization_use_case: CreateOrganizationUseCase = Depends(create_organization_use_case_factory),
    authenticated_user: AuthenticatedUserView = Depends(get_authenticated_user),
) -> OrganizationResponse:
    try:
        command = CreateOrganizationCommand(name=body.name)
        result = await create_organization_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing create_organization use case",
            extra={
                "authenticated_user_id": authenticated_user.id,
                "organization_name": body.name,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()

    match result:
        case CreateOrganizationUseCaseSuccess(organization=organization):
            return OrganizationResponse.model_validate(organization, from_attributes=True)
        case OrganizationAlreadyExistsError(name=name):
            raise OrganizationAlreadyExistsHTTPException(name)
