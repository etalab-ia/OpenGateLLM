from dataclasses import dataclass

from api.domain.provider import ProviderRepository
from api.domain.provider.entities import Provider
from api.domain.provider.errors import ProviderNotFoundError
from api.domain.user import UserWithRoleQuery


@dataclass
class GetOneProviderCommand:
    provider_id: int


@dataclass
class GetOneProviderUseCaseSuccess:
    provider: Provider


type GetOneProviderUseCaseResult = GetOneProviderUseCaseSuccess | ProviderNotFoundError


class GetOneProviderUseCase:
    def __init__(self, provider_repository: ProviderRepository, user_with_role_query: UserWithRoleQuery):
        self.provider_repository = provider_repository

    async def execute(self, command: GetOneProviderCommand) -> GetOneProviderUseCaseResult:
        provider = await self.provider_repository.get_one_provider(command.provider_id)

        if not provider:
            return ProviderNotFoundError(id=command.provider_id)
        return GetOneProviderUseCaseSuccess(provider=provider)
