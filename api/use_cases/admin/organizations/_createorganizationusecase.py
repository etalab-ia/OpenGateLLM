from dataclasses import dataclass

from api.domain.organization import OrganizationRepository
from api.domain.organization.entities import Organization
from api.domain.organization.errors import OrganizationAlreadyExistsError


@dataclass
class CreateOrganizationCommand:
    name: str


@dataclass
class CreateOrganizationUseCaseSuccess:
    organization: Organization


type CreateOrganizationUseCaseResult = CreateOrganizationUseCaseSuccess | OrganizationAlreadyExistsError


class CreateOrganizationUseCase:
    def __init__(self, organization_repository: OrganizationRepository):
        self.organization_repository = organization_repository

    async def execute(self, command: CreateOrganizationCommand) -> CreateOrganizationUseCaseResult:
        result = await self.organization_repository.create_organization(name=command.name)

        match result:
            case Organization() as organization:
                return CreateOrganizationUseCaseSuccess(organization=organization)
            case error:
                return error
