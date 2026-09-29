from fastapi import Body, Depends, Path, Query, Security

from api.dependencies import (
    create_organization_use_case_factory,
    delete_organization_use_case_factory,
    get_one_organization_use_case_factory,
    get_organizations_use_case_factory,
    update_organization_use_case_factory,
)
from api.domain import SortOrder
from api.domain.organization.entities import OrganizationSortField
from api.domain.organization.errors import (
    OrganizationAlreadyExistsError,
    OrganizationHasUsersError,
    OrganizationNotFoundError,
    UserCannotCreateOrganizationError,
)
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.fastapi.accesscontroller import AccessController
from api.infrastructure.fastapi.dependencies import get_authenticated_user
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.admin import router
from api.infrastructure.fastapi.endpoints.exceptions import (
    NotAdminUserHTTPException,
    OrganizationAlreadyExistsHTTPException,
    OrganizationHasUsersHTTPException,
    OrganizationNotFoundHTTPException,
    UnauthorizedActionHTTPException,
)
from api.infrastructure.fastapi.routes import EndpointRoute
from api.infrastructure.fastapi.schemas.admin.organizations import (
    CreateOrganizationBody,
    OrganizationResponse,
    OrganizationsResponse,
    UpdateOrganizationBody,
)
from api.use_cases.admin.organizations import (
    CreateOrganizationCommand,
    CreateOrganizationUseCase,
    CreateOrganizationUseCaseSuccess,
    DeleteOrganizationCommand,
    DeleteOrganizationUseCase,
    DeleteOrganizationUseCaseSuccess,
    GetOneOrganizationCommand,
    GetOneOrganizationUseCase,
    GetOneOrganizationUseCaseSuccess,
    GetOrganizationsCommand,
    GetOrganizationsUseCase,
    GetOrganizationsUseCaseSuccess,
    UpdateOrganizationCommand,
    UpdateOrganizationUseCase,
    UpdateOrganizationUseCaseSuccess,
)


@router.post(
    path=EndpointRoute.ADMIN_ORGANIZATIONS,
    dependencies=[Security(dependency=AccessController())],
    status_code=201,
    responses=get_documentation_responses([UnauthorizedActionHTTPException, OrganizationAlreadyExistsHTTPException]),
)
async def create_organization(
    body: CreateOrganizationBody = Body(description="The organization creation request."),
    create_organization_use_case: CreateOrganizationUseCase = Depends(create_organization_use_case_factory),
    authenticated_user: AuthenticatedUserView = Depends(get_authenticated_user),
) -> OrganizationResponse:
    command = CreateOrganizationCommand(authenticated_user_id=authenticated_user.id, name=body.name)
    result = await create_organization_use_case.execute(command)

    match result:
        case CreateOrganizationUseCaseSuccess(organization=organization):
            return OrganizationResponse.model_validate(organization, from_attributes=True)
        case OrganizationAlreadyExistsError(name=name):
            raise OrganizationAlreadyExistsHTTPException(name)
        case UserCannotCreateOrganizationError(user_id=user_id):
            raise UnauthorizedActionHTTPException(user_id)


@router.get(
    path=EndpointRoute.ADMIN_ORGANIZATIONS,
    dependencies=[Security(dependency=AccessController(only_admin=True))],
    status_code=200,
    responses=get_documentation_responses([NotAdminUserHTTPException]),
)
async def get_organizations(
    offset: int = Query(default=0, ge=0, description="Number of organizations to skip."),
    limit: int = Query(default=10, ge=1, le=100, description="Maximum number of organizations to return."),
    sort_by: OrganizationSortField = Query(default=OrganizationSortField.ID, description="Field to sort by."),
    sort_order: SortOrder = Query(default=SortOrder.ASC, description="Sort order."),
    get_organizations_use_case: GetOrganizationsUseCase = Depends(get_organizations_use_case_factory),
) -> OrganizationsResponse:
    command = GetOrganizationsCommand(offset=offset, limit=limit, sort_by=sort_by, sort_order=sort_order)
    result = await get_organizations_use_case.execute(command)

    match result:
        case GetOrganizationsUseCaseSuccess(organization_page=organization_page):
            return OrganizationsResponse(
                total=organization_page.total,
                offset=offset,
                limit=limit,
                data=[OrganizationResponse.model_validate(organization, from_attributes=True) for organization in organization_page.data],
            )


@router.get(
    path=EndpointRoute.ADMIN_ORGANIZATIONS + "/{organization_id}",
    dependencies=[Security(dependency=AccessController(only_admin=True))],
    status_code=200,
    responses=get_documentation_responses([NotAdminUserHTTPException, OrganizationNotFoundHTTPException]),
)
async def get_organization(
    organization_id: int = Path(description="The ID of the organization to get."),
    get_one_organization_use_case: GetOneOrganizationUseCase = Depends(get_one_organization_use_case_factory),
) -> OrganizationResponse:
    command = GetOneOrganizationCommand(organization_id=organization_id)
    result = await get_one_organization_use_case.execute(command)

    match result:
        case GetOneOrganizationUseCaseSuccess(organization=organization):
            return OrganizationResponse.model_validate(organization, from_attributes=True)
        case OrganizationNotFoundError(id=not_found_organization_id):
            raise OrganizationNotFoundHTTPException(not_found_organization_id)


@router.delete(
    path=EndpointRoute.ADMIN_ORGANIZATIONS + "/{organization_id}",
    dependencies=[Security(dependency=AccessController(only_admin=True))],
    status_code=200,
    responses=get_documentation_responses([NotAdminUserHTTPException, OrganizationNotFoundHTTPException, OrganizationHasUsersHTTPException]),
)
async def delete_organization(
    organization_id: int = Path(description="The ID of the organization to delete."),
    delete_organization_use_case: DeleteOrganizationUseCase = Depends(delete_organization_use_case_factory),
) -> OrganizationResponse:
    command = DeleteOrganizationCommand(organization_id=organization_id)
    result = await delete_organization_use_case.execute(command)

    match result:
        case DeleteOrganizationUseCaseSuccess(organization=organization):
            return OrganizationResponse.model_validate(organization, from_attributes=True)
        case OrganizationNotFoundError(id=organization_id):
            raise OrganizationNotFoundHTTPException(organization_id)
        case OrganizationHasUsersError(id=organization_id):
            raise OrganizationHasUsersHTTPException(organization_id=organization_id)


@router.patch(
    path=EndpointRoute.ADMIN_ORGANIZATIONS + "/{organization_id}",
    dependencies=[Security(dependency=AccessController(only_admin=True))],
    status_code=200,
    responses=get_documentation_responses([NotAdminUserHTTPException, OrganizationNotFoundHTTPException, OrganizationAlreadyExistsHTTPException]),
)
async def update_organization(
    organization_id: int = Path(description="The ID of the organization to update."),
    body: UpdateOrganizationBody = Body(description="The organization update request."),
    update_organization_use_case: UpdateOrganizationUseCase = Depends(update_organization_use_case_factory),
) -> OrganizationResponse:
    command = UpdateOrganizationCommand(organization_id=organization_id, name=body.name)
    result = await update_organization_use_case.execute(command)

    match result:
        case UpdateOrganizationUseCaseSuccess(organization=organization):
            return OrganizationResponse.model_validate(organization, from_attributes=True)
        case OrganizationNotFoundError(id=not_found_organization_id):
            raise OrganizationNotFoundHTTPException(not_found_organization_id)
        case OrganizationAlreadyExistsError(name=name):
            raise OrganizationAlreadyExistsHTTPException(name)
