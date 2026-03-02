from dataclasses import dataclass

from api.domain.provider import ProviderRepository
from api.domain.provider.entities import Provider
from api.domain.provider.errors import ProviderNotFoundError
from api.domain.userinfo import UserInfoRepository
from api.domain.userinfo.errors import UserIsNotAdminError


@dataclass
class DeleteProviderCommand:
    provider_id: int
    user_id: int


@dataclass
class DeleteProviderUseCaseSuccess:
    deleted_provider: Provider


type DeleteProviderUseCaseResult = DeleteProviderUseCaseSuccess | ProviderNotFoundError | UserIsNotAdminError


class DeleteProviderUseCase:
    def __init__(
        self,
        provider_repository: ProviderRepository,
        user_info_repository: UserInfoRepository,
    ):
        self.provider_repository = provider_repository
        self.user_info_repository = user_info_repository

    async def execute(self, command: DeleteProviderCommand) -> DeleteProviderUseCaseResult:
        user_info = await self.user_info_repository.get_user_info(user_id=command.user_id)

        if not user_info.is_admin:
            return UserIsNotAdminError()

        provider = await self.provider_repository.delete_provider(command.provider_id)

        if provider is None:
            return ProviderNotFoundError(command.provider_id)
        return DeleteProviderUseCaseSuccess(deleted_provider=provider)
