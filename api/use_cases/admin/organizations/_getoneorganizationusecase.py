from dataclasses import dataclass

from api.domain.organization import OrganizationRepository
from api.domain.organization.entities import Organization
from api.domain.organization.errors import OrganizationNotFoundError


@dataclass
class GetOneOrganizationCommand:
    organization_id: int


@dataclass
class GetOneOrganizationUseCaseSuccess:
    organization: Organization


type GetOneOrganizationUseCaseResult = GetOneOrganizationUseCaseSuccess | OrganizationNotFoundError


class GetOneOrganizationUseCase:
    def __init__(self, organization_repository: OrganizationRepository):
        self.organization_repository = organization_repository

    async def execute(self, command: GetOneOrganizationCommand) -> GetOneOrganizationUseCaseResult:
        result = await self.organization_repository.get_organization_by_id(organization_id=command.organization_id)

        match result:
            case Organization() as organization:
                return GetOneOrganizationUseCaseSuccess(organization=organization)
            case OrganizationNotFoundError():
                return OrganizationNotFoundError(id=command.organization_id)
