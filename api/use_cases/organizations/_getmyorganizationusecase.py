from dataclasses import dataclass

from api.domain.organization import OrganizationRepository
from api.domain.organization.entities import Organization
from api.domain.organization.errors import OrganizationNotFoundError


@dataclass
class GetMyOrganizationCommand:
    organization_id: int


@dataclass
class GetMyOrganizationUseCaseSuccess:
    organization: Organization


type GetMyOrganizationUseCaseResult = GetMyOrganizationUseCaseSuccess | OrganizationNotFoundError


class GetMyOrganizationUseCase:
    def __init__(self, organization_repository: OrganizationRepository):
        self.organization_repository = organization_repository

    async def execute(self, command: GetMyOrganizationCommand) -> GetMyOrganizationUseCaseResult:
        result = await self.organization_repository.get_organization_by_id(organization_id=command.organization_id)

        match result:
            case Organization() as organization:
                return GetMyOrganizationUseCaseSuccess(organization=organization)
            case OrganizationNotFoundError():
                return OrganizationNotFoundError(id=command.organization_id)
