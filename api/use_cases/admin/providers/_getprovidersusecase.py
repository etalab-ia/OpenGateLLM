from dataclasses import dataclass

from api.domain import SortOrder
from api.domain.provider import ProviderRepository
from api.domain.provider.entities import ProviderPage, ProviderSortField
from api.domain.userinfo import UserInfoRepository
from api.domain.userinfo.errors import UserIsNotAdminError


@dataclass
class GetProvidersCommand:
    user_id: int
    router_id: int | None
    offset: int
    limit: int
    sort_by: ProviderSortField
    sort_order: SortOrder


@dataclass
class GetProvidersUseCaseSuccess:
    page: ProviderPage


type GetProvidersUseCaseResult = GetProvidersUseCaseSuccess | UserIsNotAdminError


class GetProvidersUseCase:
    def __init__(self, provider_repository: ProviderRepository, user_info_repository: UserInfoRepository):
        self.provider_repository = provider_repository
        self.user_info_repository = user_info_repository

    async def execute(
        self,
        command: GetProvidersCommand,
    ) -> GetProvidersUseCaseResult:
        user_info = await self.user_info_repository.get_user_info(user_id=command.user_id)

        if not user_info.is_admin:
            return UserIsNotAdminError()

        providers_page = await self.provider_repository.get_providers_page(
            router_id=command.router_id, limit=command.limit, offset=command.offset, sort_by=command.sort_by, sort_order=command.sort_order
        )

        return GetProvidersUseCaseSuccess(page=providers_page)
