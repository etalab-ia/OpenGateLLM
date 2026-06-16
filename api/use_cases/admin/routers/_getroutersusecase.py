from dataclasses import dataclass

from api.domain import SortField, SortOrder
from api.domain.key import KeyRepository
from api.domain.router import RouterRepository
from api.domain.router.entities import RouterPage
from api.domain.user import UserWithRoleQuery
from api.domain.user.errors import UserIsNotAdminError


@dataclass
class GetRoutersCommand:
    offset: int
    limit: int
    sort_by: SortField
    sort_order: SortOrder


@dataclass
class GetRoutersUseCaseSuccess:
    router_page: RouterPage


type GetRoutersUseCaseResult = GetRoutersUseCaseSuccess | UserIsNotAdminError


class GetRoutersUseCase:
    def __init__(self, key_repository: KeyRepository, router_repository: RouterRepository, user_with_role_query: UserWithRoleQuery):
        self.key_repository = key_repository
        self.router_repository = router_repository
        self.user_with_role_query = user_with_role_query

    async def execute(self, command: GetRoutersCommand) -> GetRoutersUseCaseResult:
        router_page = await self.router_repository.get_routers_page(
            limit=command.limit,
            offset=command.offset,
            sort_by=command.sort_by,
            sort_order=command.sort_order,
        )

        return GetRoutersUseCaseSuccess(router_page=router_page)
