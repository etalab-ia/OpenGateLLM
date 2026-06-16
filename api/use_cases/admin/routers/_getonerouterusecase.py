from dataclasses import dataclass

from api.domain.router import RouterRepository
from api.domain.router.entities import Router
from api.domain.router.errors import RouterNotFoundError


@dataclass
class GetOneRouterCommand:
    router_id: int


@dataclass
class GetOneRouterUseCaseSuccess:
    router: Router


type GetOneRouterUseCaseResult = GetOneRouterUseCaseSuccess | RouterNotFoundError


class GetOneRouterUseCase:
    def __init__(self, router_repository: RouterRepository):
        self.router_repository = router_repository

    async def execute(self, command: GetOneRouterCommand) -> GetOneRouterUseCaseResult:
        router = await self.router_repository.get_router_by_id(command.router_id)

        if not router:
            return RouterNotFoundError(id=command.router_id)
        return GetOneRouterUseCaseSuccess(router=router)
