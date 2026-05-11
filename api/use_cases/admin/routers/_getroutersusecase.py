from dataclasses import dataclass
import time

from api.domain import SortField, SortOrder
from api.domain.router import RouterRepository
from api.domain.router.entities import RouterPage
from api.domain.user import UserWithRoleQuery
from api.domain.user.errors import UserExpiredError, UserIsNotAdminError


@dataclass
class GetRoutersCommand:
    user_id: int
    offset: int
    limit: int
    sort_by: SortField
    sort_order: SortOrder


@dataclass
class GetRoutersUseCaseSuccess:
    router_page: RouterPage


type GetRoutersUseCaseResult = GetRoutersUseCaseSuccess | UserIsNotAdminError


class GetRoutersUseCase:
    def __init__(self, router_repository: RouterRepository, user_with_role_query: UserWithRoleQuery):
        self.router_repository = router_repository
        self.user_with_role_query = user_with_role_query

    async def execute(
        self,
        command: GetRoutersCommand,
    ) -> GetRoutersUseCaseResult:
        user = await self.user_with_role_query.get_user_with_role_by_id(user_id=command.user_id)

        if user.expires is not None and user.expires < time.time():
            return UserExpiredError()

        if not user.is_admin:
            return UserIsNotAdminError()

        router_page = await self.router_repository.get_routers_page(
            limit=command.limit,
            offset=command.offset,
            sort_by=command.sort_by,
            sort_order=command.sort_order,
        )

        return GetRoutersUseCaseSuccess(router_page=router_page)
