from dataclasses import dataclass

from api.domain.organization import OrganizationAuthorization, OrganizationRepository
from api.domain.organization.entities import Organization
from api.domain.organization.errors import OrganizationAlreadyExistsError, UserCannotCreateOrganizationError


@dataclass
class CreateOrganizationCommand:
    authenticated_user_id: int
    name: str


@dataclass
class CreateOrganizationUseCaseSuccess:
    organization: Organization


type CreateOrganizationUseCaseResult = CreateOrganizationUseCaseSuccess | OrganizationAlreadyExistsError | UserCannotCreateOrganizationError


class CreateOrganizationUseCase:
    def __init__(self, organization_repository: OrganizationRepository, organization_authorization: OrganizationAuthorization):
        self.organization_repository = organization_repository
        self.organization_authorization = organization_authorization

    async def execute(self, command: CreateOrganizationCommand) -> CreateOrganizationUseCaseResult:
        is_authorized = await self.organization_authorization.can_create_organization(user_id=command.authenticated_user_id)

        if not is_authorized:
            return UserCannotCreateOrganizationError(user_id=command.authenticated_user_id)

        result = await self.organization_repository.create_organization(name=command.name)

        match result:
            case Organization() as organization:
                await self.organization_authorization.attach_organization_to_platform(organization_id=organization.id)
                return CreateOrganizationUseCaseSuccess(organization=organization)
            case error:
                return error
