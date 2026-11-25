from dataclasses import dataclass

from api.domain import SortField, SortOrder
from api.domain.router import RouterAuthorization, RouterRepository
from api.domain.router.entities import RouterPage
from api.domain.router.errors import UserCannotReadRouterError


@dataclass
class GetRoutersCommand:
    authenticated_user_id: int
    offset: int
    limit: int
    sort_by: SortField
    sort_order: SortOrder


@dataclass
class GetRoutersUseCaseSuccess:
    router_page: RouterPage


type GetRoutersUseCaseResult = GetRoutersUseCaseSuccess | UserCannotReadRouterError


class GetRoutersUseCase:
    def __init__(self, router_repository: RouterRepository, router_authorization: RouterAuthorization):
        self.router_repository = router_repository
        self.router_authorization = router_authorization

    async def execute(self, command: GetRoutersCommand) -> GetRoutersUseCaseResult:
        is_authorized = await self.router_authorization.can_read_router(user_id=command.authenticated_user_id)

        if not is_authorized:
            return UserCannotReadRouterError(user_id=command.authenticated_user_id)

        router_page = await self.router_repository.get_routers_page(
            limit=command.limit,
            offset=command.offset,
            sort_by=command.sort_by,
            sort_order=command.sort_order,
        )

        return GetRoutersUseCaseSuccess(router_page=router_page)
