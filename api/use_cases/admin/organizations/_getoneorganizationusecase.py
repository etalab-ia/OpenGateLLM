from dataclasses import dataclass

from api.domain.organization import OrganizationAuthorization, OrganizationRepository
from api.domain.organization.entities import Organization
from api.domain.organization.errors import OrganizationNotFoundError, UserCannotReadOrganizationError


@dataclass
class GetOneOrganizationCommand:
    authenticated_user_id: int
    organization_id: int


@dataclass
class GetOneOrganizationUseCaseSuccess:
    organization: Organization


type GetOneOrganizationUseCaseResult = GetOneOrganizationUseCaseSuccess | OrganizationNotFoundError | UserCannotReadOrganizationError


class GetOneOrganizationUseCase:
    def __init__(self, organization_repository: OrganizationRepository, organization_authorization: OrganizationAuthorization):
        self.organization_repository = organization_repository
        self.organization_authorization = organization_authorization

    async def execute(self, command: GetOneOrganizationCommand) -> GetOneOrganizationUseCaseResult:
        is_authorized = await self.organization_authorization.can_read_organization(user_id=command.authenticated_user_id)

        if not is_authorized:
            return UserCannotReadOrganizationError(user_id=command.authenticated_user_id)

        result = await self.organization_repository.get_organization_by_id(organization_id=command.organization_id)

        match result:
            case Organization() as organization:
                return GetOneOrganizationUseCaseSuccess(organization=organization)
            case OrganizationNotFoundError():
                return OrganizationNotFoundError(id=command.organization_id)
