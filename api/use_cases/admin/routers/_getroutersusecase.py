from dataclasses import dataclass

from api.domain import SortField, SortOrder
from api.domain.router import RouterRepository
from api.domain.router.entities import RouterPage


@dataclass
class GetRoutersCommand:
    offset: int
    limit: int
    sort_by: SortField
    sort_order: SortOrder


@dataclass
class GetRoutersUseCaseSuccess:
    router_page: RouterPage


type GetRoutersUseCaseResult = GetRoutersUseCaseSuccess


class GetRoutersUseCase:
    def __init__(self, router_repository: RouterRepository):
        self.router_repository = router_repository

    async def execute(self, command: GetRoutersCommand) -> GetRoutersUseCaseResult:
        router_page = await self.router_repository.get_routers_page(
            limit=command.limit,
            offset=command.offset,
            sort_by=command.sort_by,
            sort_order=command.sort_order,
        )

        return GetRoutersUseCaseSuccess(router_page=router_page)
