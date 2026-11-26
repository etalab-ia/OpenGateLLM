from dataclasses import dataclass

from api.domain.router import RouterAuthorization, RouterRepository
from api.domain.router.entities import Router
from api.domain.router.errors import RouterNotFoundError, UserCannotReadRouterError


@dataclass
class GetOneRouterCommand:
    authenticated_user_id: int
    router_id: int


@dataclass
class GetOneRouterUseCaseSuccess:
    router: Router


type GetOneRouterUseCaseResult = GetOneRouterUseCaseSuccess | RouterNotFoundError | UserCannotReadRouterError


class GetOneRouterUseCase:
    def __init__(self, router_repository: RouterRepository, router_authorization: RouterAuthorization):
        self.router_repository = router_repository
        self.router_authorization = router_authorization

    async def execute(self, command: GetOneRouterCommand) -> GetOneRouterUseCaseResult:
        is_authorized = await self.router_authorization.can_read_router(user_id=command.authenticated_user_id)

        if not is_authorized:
            return UserCannotReadRouterError(user_id=command.authenticated_user_id)

        router = await self.router_repository.get_router_by_id(command.router_id)

        if not router:
            return RouterNotFoundError(id=command.router_id)
        return GetOneRouterUseCaseSuccess(router=router)
