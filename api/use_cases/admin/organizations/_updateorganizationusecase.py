from dataclasses import dataclass

from api.domain.organization import OrganizationRepository
from api.domain.organization.entities import Organization
from api.domain.organization.errors import OrganizationAlreadyExistsError, OrganizationNotFoundError


@dataclass
class UpdateOrganizationCommand:
    """Full replacement of the organization persisted fields."""

    organization_id: int
    name: str


@dataclass
class UpdateOrganizationUseCaseSuccess:
    organization: Organization


type UpdateOrganizationUseCaseResult = UpdateOrganizationUseCaseSuccess | OrganizationAlreadyExistsError | OrganizationNotFoundError


class UpdateOrganizationUseCase:
    def __init__(self, organization_repository: OrganizationRepository):
        self.organization_repository = organization_repository

    async def execute(self, command: UpdateOrganizationCommand) -> UpdateOrganizationUseCaseResult:
        organization = await self.organization_repository.get_organization_by_id(organization_id=command.organization_id)
        if isinstance(organization, OrganizationNotFoundError):
            return OrganizationNotFoundError(id=command.organization_id)

        organization_to_persist = organization.with_name(command.name)

        if organization_to_persist == organization:
            return UpdateOrganizationUseCaseSuccess(organization=organization)

        result = await self.organization_repository.update_organization(organization=organization_to_persist)

        match result:
            case Organization() as updated_organization:
                return UpdateOrganizationUseCaseSuccess(organization=updated_organization)
            case error:
                return error
