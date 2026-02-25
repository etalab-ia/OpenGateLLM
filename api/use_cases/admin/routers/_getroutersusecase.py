from dataclasses import dataclass

from api.domain.router import RouterRepository
from api.domain.router.entities import Router, RouterSortField, SortOrder
from api.domain.userinfo import UserInfoRepository
from api.domain.userinfo.errors import UserIsNotAdminError


@dataclass
class GetRoutersCommand:
    user_id: int
    offset: int
    limit: int
    sort_by: RouterSortField
    sort_order: SortOrder


@dataclass
class GetRoutersUseCaseSuccess:
    routers: list[Router]
    total: int


type GetRoutersUseCaseResult = GetRoutersUseCaseSuccess | UserIsNotAdminError


class GetRoutersUseCase:
    def __init__(self, router_repository: RouterRepository, user_info_repository: UserInfoRepository):
        self.router_repository = router_repository
        self.user_info_repository = user_info_repository

    async def execute(
        self,
        command: GetRoutersCommand,
    ) -> GetRoutersUseCaseResult:
        user_info = await self.user_info_repository.get_user_info(user_id=command.user_id)

        if not user_info.is_admin:
            return UserIsNotAdminError()

        router_page = await self.router_repository.get_routers_page(
            limit=command.limit,
            offset=command.offset,
            sort_by=command.sort_by,
            sort_order=command.sort_order,
        )

        return GetRoutersUseCaseSuccess(routers=router_page.data, total=router_page.total)
