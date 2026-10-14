from dataclasses import dataclass

from api.domain.organization import OrganizationAuthorization, OrganizationRepository
from api.domain.organization.entities import Organization
from api.domain.organization.errors import OrganizationHasUsersError, OrganizationNotFoundError, UserCannotDeleteOrganizationError


@dataclass
class DeleteOrganizationCommand:
    authenticated_user_id: int
    organization_id: int


@dataclass
class DeleteOrganizationUseCaseSuccess:
    organization: Organization


type DeleteOrganizationUseCaseResult = (
    DeleteOrganizationUseCaseSuccess | OrganizationHasUsersError | OrganizationNotFoundError | UserCannotDeleteOrganizationError
)


class DeleteOrganizationUseCase:
    def __init__(self, organization_repository: OrganizationRepository, organization_authorization: OrganizationAuthorization):
        self.organization_repository = organization_repository
        self.organization_authorization = organization_authorization

    async def execute(self, command: DeleteOrganizationCommand) -> DeleteOrganizationUseCaseResult:
        is_authorized = await self.organization_authorization.can_delete_organization(
            user_id=command.authenticated_user_id, organization_id=command.organization_id
        )

        if not is_authorized:
            return UserCannotDeleteOrganizationError(user_id=command.authenticated_user_id)

        result = await self.organization_repository.get_organization_by_id(organization_id=command.organization_id)
        match result:
            case Organization() as organization:
                if organization.users > 0:
                    return OrganizationHasUsersError(id=command.organization_id)
            case OrganizationNotFoundError():
                return OrganizationNotFoundError(id=command.organization_id)

        delete_result = await self.organization_repository.delete_organization(organization_id=command.organization_id)
        match delete_result:
            case Organization() as organization:
                await self.organization_authorization.detach_organization_from_platform(organization_id=organization.id)
                return DeleteOrganizationUseCaseSuccess(organization=organization)
            case OrganizationHasUsersError() as error:
                return error
            case OrganizationNotFoundError() as error:
                return error
