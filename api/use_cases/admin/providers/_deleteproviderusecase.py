from dataclasses import dataclass

from api.domain.provider import ProviderRepository
from api.domain.provider.entities import Provider
from api.domain.provider.errors import ProviderNotFoundError
from api.domain.user import UserWithRoleQuery
from api.domain.user.errors import UserExpiredError, UserIsNotAdminError


@dataclass
class DeleteProviderCommand:
    provider_id: int
    user_id: int


@dataclass
class DeleteProviderUseCaseSuccess:
    deleted_provider: Provider


type DeleteProviderUseCaseResult = DeleteProviderUseCaseSuccess | ProviderNotFoundError | UserExpiredError | UserIsNotAdminError


class DeleteProviderUseCase:
    def __init__(
        self,
        provider_repository: ProviderRepository,
        user_with_role_query: UserWithRoleQuery,
    ):
        self.provider_repository = provider_repository
        self.user_with_role_query = user_with_role_query

    async def execute(self, command: DeleteProviderCommand) -> DeleteProviderUseCaseResult:
        user = await self.user_with_role_query.get_user_with_role_by_id(user_id=command.user_id)

        if user.has_expired:
            return UserExpiredError()

        if not user.is_admin:
            return UserIsNotAdminError()

        provider = await self.provider_repository.delete_provider(command.provider_id)

        match provider:
            case Provider() as deleted_provider:
                return DeleteProviderUseCaseSuccess(deleted_provider=deleted_provider)
            case ProviderNotFoundError(id=not_found_id):
                return ProviderNotFoundError(id=not_found_id)
