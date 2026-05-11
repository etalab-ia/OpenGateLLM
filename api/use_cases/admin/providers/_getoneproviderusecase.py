from dataclasses import dataclass
import time

from api.domain.provider import ProviderRepository
from api.domain.provider.entities import Provider
from api.domain.provider.errors import ProviderNotFoundError
from api.domain.user import UserWithRoleQuery
from api.domain.user.errors import UserExpiredError, UserIsNotAdminError


@dataclass
class GetOneProviderCommand:
    user_id: int
    provider_id: int


@dataclass
class GetOneProviderUseCaseSuccess:
    provider: Provider


type GetOneProviderUseCaseResult = GetOneProviderUseCaseSuccess | ProviderNotFoundError | UserExpiredError | UserIsNotAdminError


class GetOneProviderUseCase:
    def __init__(self, provider_repository: ProviderRepository, user_with_role_query: UserWithRoleQuery):
        self.provider_repository = provider_repository
        self.user_with_role_query = user_with_role_query

    async def execute(
        self,
        command: GetOneProviderCommand,
    ) -> GetOneProviderUseCaseResult:
        user = await self.user_with_role_query.get_user_with_role_by_id(user_id=command.user_id)

        if user.expires is not None and user.expires < time.time():
            return UserExpiredError()

        if not user.is_admin:
            return UserIsNotAdminError()

        provider = await self.provider_repository.get_one_provider(command.provider_id)

        if not provider:
            return ProviderNotFoundError(id=command.provider_id)
        return GetOneProviderUseCaseSuccess(provider=provider)
