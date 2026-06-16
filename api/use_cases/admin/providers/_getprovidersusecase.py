from dataclasses import dataclass

from api.domain import SortOrder
from api.domain.provider import ProviderRepository
from api.domain.provider.entities import ProviderPage, ProviderSortField
from api.domain.user import UserWithRoleQuery


@dataclass
class GetProvidersCommand:
    router_id: int | None
    offset: int
    limit: int
    sort_by: ProviderSortField
    sort_order: SortOrder


@dataclass
class GetProvidersUseCaseSuccess:
    page: ProviderPage


type GetProvidersUseCaseResult = GetProvidersUseCaseSuccess


class GetProvidersUseCase:
    def __init__(self, provider_repository: ProviderRepository, user_with_role_query: UserWithRoleQuery):
        self.provider_repository = provider_repository

    async def execute(self, command: GetProvidersCommand) -> GetProvidersUseCaseResult:
        providers_page = await self.provider_repository.get_providers_page(
            router_id=command.router_id, limit=command.limit, offset=command.offset, sort_by=command.sort_by, sort_order=command.sort_order
        )

        return GetProvidersUseCaseSuccess(page=providers_page)
