from dataclasses import dataclass

from api.domain.router import RouterRepository
from api.domain.router.entities import Router
from api.domain.router.errors import RouterNotFoundError


@dataclass
class DeleteRouterCommand:
    router_id: int


@dataclass
class DeleteRouterUseCaseSuccess:
    router: Router


type DeleteRouterUseCaseResult = DeleteRouterUseCaseSuccess | RouterNotFoundError


class DeleteRouterUseCase:
    def __init__(self, router_repository: RouterRepository):
        self.router_repository = router_repository

    async def execute(self, command: DeleteRouterCommand) -> DeleteRouterUseCaseResult:
        result = await self.router_repository.delete_router(command.router_id)

        match result:
            case Router() as deleted_router:
                return DeleteRouterUseCaseSuccess(router=deleted_router)
            case RouterNotFoundError(id=not_found_id):
                return RouterNotFoundError(id=not_found_id)
