from dataclasses import dataclass

from api.domain.organization import OrganizationRepository
from api.domain.organization.entities import Organization
from api.domain.organization.errors import OrganizationHasUsersError, OrganizationNotFoundError


@dataclass
class DeleteOrganizationCommand:
    organization_id: int


@dataclass
class DeleteOrganizationUseCaseSuccess:
    organization: Organization


type DeleteOrganizationUseCaseResult = DeleteOrganizationUseCaseSuccess | OrganizationHasUsersError | OrganizationNotFoundError


class DeleteOrganizationUseCase:
    def __init__(self, organization_repository: OrganizationRepository):
        self.organization_repository = organization_repository

    async def execute(self, command: DeleteOrganizationCommand) -> DeleteOrganizationUseCaseResult:
        result = await self.organization_repository.get_organization_by_id(organization_id=command.organization_id)
        match result:
            case Organization() as organization:
                if organization.users > 0:
                    return OrganizationHasUsersError(id=command.organization_id, number_of_users=organization.users)
            case OrganizationNotFoundError():
                return OrganizationNotFoundError(id=command.organization_id)

        delete_result = await self.organization_repository.delete_organization(organization_id=command.organization_id)
        match delete_result:
            case Organization() as organization:
                return DeleteOrganizationUseCaseSuccess(organization=organization)
            case OrganizationNotFoundError() as error:
                return error
