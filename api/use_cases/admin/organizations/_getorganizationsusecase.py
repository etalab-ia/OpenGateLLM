from dataclasses import dataclass

from api.domain import SortOrder
from api.domain.organization import OrganizationRepository
from api.domain.organization.entities import OrganizationPage, OrganizationSortField


@dataclass
class GetOrganizationsCommand:
    offset: int = 0
    limit: int = 10
    sort_by: OrganizationSortField = OrganizationSortField.ID
    sort_order: SortOrder = SortOrder.ASC


@dataclass
class GetOrganizationsUseCaseSuccess:
    organization_page: OrganizationPage


type GetOrganizationsUseCaseResult = GetOrganizationsUseCaseSuccess


class GetOrganizationsUseCase:
    def __init__(self, organization_repository: OrganizationRepository):
        self.organization_repository = organization_repository

    async def execute(self, command: GetOrganizationsCommand) -> GetOrganizationsUseCaseResult:
        organization_page = await self.organization_repository.get_organizations_page(
            limit=command.limit,
            offset=command.offset,
            sort_by=command.sort_by,
            sort_order=command.sort_order,
        )

        return GetOrganizationsUseCaseSuccess(organization_page=organization_page)
