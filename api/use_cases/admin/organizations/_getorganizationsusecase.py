from dataclasses import dataclass

from api.domain import SortOrder
from api.domain.organization import OrganizationAuthorization, OrganizationRepository
from api.domain.organization.entities import OrganizationPage, OrganizationSortField
from api.domain.organization.errors import UserCannotReadOrganizationsError


@dataclass
class GetOrganizationsCommand:
    authenticated_user_id: int
    name: str | None = None
    offset: int = 0
    limit: int = 10
    sort_by: OrganizationSortField = OrganizationSortField.ID
    sort_order: SortOrder = SortOrder.ASC


@dataclass
class GetOrganizationsUseCaseSuccess:
    organization_page: OrganizationPage


type GetOrganizationsUseCaseResult = GetOrganizationsUseCaseSuccess | UserCannotReadOrganizationsError


class GetOrganizationsUseCase:
    def __init__(self, organization_repository: OrganizationRepository, organization_authorization: OrganizationAuthorization):
        self.organization_repository = organization_repository
        self.organization_authorization = organization_authorization

    async def execute(self, command: GetOrganizationsCommand) -> GetOrganizationsUseCaseResult:
        is_authorized = await self.organization_authorization.can_read_organizations(user_id=command.authenticated_user_id)

        if not is_authorized:
            return UserCannotReadOrganizationsError(user_id=command.authenticated_user_id)

        organization_page = await self.organization_repository.get_organizations_page(
            name=command.name,
            limit=command.limit,
            offset=command.offset,
            sort_by=command.sort_by,
            sort_order=command.sort_order,
        )

        return GetOrganizationsUseCaseSuccess(organization_page=organization_page)
