from dataclasses import dataclass
import time

from api.domain import SortOrder
from api.domain.provider import ProviderRepository
from api.domain.provider.entities import ProviderPage, ProviderSortField
from api.domain.user import UserWithRoleQuery
from api.domain.user.errors import UserExpiredError, UserIsNotAdminError


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


type GetProvidersUseCaseResult = GetProvidersUseCaseSuccess | UserExpiredError | UserIsNotAdminError


class GetProvidersUseCase:
    def __init__(self, provider_repository: ProviderRepository, user_with_role_query: UserWithRoleQuery):
        self.provider_repository = provider_repository
        self.user_with_role_query = user_with_role_query

    async def execute(
        self,
        command: GetProvidersCommand,
    ) -> GetProvidersUseCaseResult:
        user = await self.user_with_role_query.get_user_with_role_by_id(user_id=command.user_id)

        if user.expires is not None and user.expires < time.time():
            return UserExpiredError()

        if not user.is_admin:
            return UserIsNotAdminError()

        providers_page = await self.provider_repository.get_providers_page(
            router_id=command.router_id, limit=command.limit, offset=command.offset, sort_by=command.sort_by, sort_order=command.sort_order
        )

        return GetProvidersUseCaseSuccess(page=providers_page)
