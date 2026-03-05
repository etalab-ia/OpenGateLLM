from dataclasses import dataclass

from api.domain.provider import Provider, ProviderRepository
from api.domain.provider.errors import ProviderNotFoundError
from api.domain.userinfo import UserInfoRepository
from api.domain.userinfo.errors import UserIsNotAdminError


@dataclass
class GetOneProviderCommand:
    user_id: int
    provider_id: int


@dataclass
class GetOneProviderUseCaseSuccess:
    provider: Provider


type GetOneProviderUseCaseResult = GetOneProviderUseCaseSuccess | ProviderNotFoundError | UserIsNotAdminError


class GetOneProviderUseCase:
    def __init__(self, provider_repository: ProviderRepository, user_info_repository: UserInfoRepository):
        self.provider_repository = provider_repository
        self.user_info_repository = user_info_repository

    async def execute(
        self,
        command: GetOneProviderCommand,
    ) -> GetOneProviderUseCaseResult:
        user_info = await self.user_info_repository.get_user_info(user_id=command.user_id)

        if not user_info.is_admin:
            return UserIsNotAdminError()

        provider = await self.provider_repository.get_one_provider(command.provider_id)

        if not provider:
            return ProviderNotFoundError(command.provider_id)
        return GetOneProviderUseCaseSuccess(provider=provider)
