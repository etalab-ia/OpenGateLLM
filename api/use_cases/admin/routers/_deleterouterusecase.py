from dataclasses import dataclass

from api.domain.router import RouterAuthorization, RouterRepository
from api.domain.router.entities import Router
from api.domain.router.errors import RouterNotFoundError, UserCannotDeleteRouterError


@dataclass
class DeleteRouterCommand:
    authenticated_user_id: int
    router_id: int


@dataclass
class DeleteRouterUseCaseSuccess:
    router: Router


type DeleteRouterUseCaseResult = DeleteRouterUseCaseSuccess | RouterNotFoundError | UserCannotDeleteRouterError


class DeleteRouterUseCase:
    def __init__(self, router_repository: RouterRepository, router_authorization: RouterAuthorization):
        self.router_repository = router_repository
        self.router_authorization = router_authorization

    async def execute(self, command: DeleteRouterCommand) -> DeleteRouterUseCaseResult:
        is_authorized = await self.router_authorization.can_delete_router(user_id=command.authenticated_user_id, router_id=command.router_id)

        if not is_authorized:
            return UserCannotDeleteRouterError(user_id=command.authenticated_user_id)

        result = await self.router_repository.delete_router(command.router_id)

        match result:
            case Router() as deleted_router:
                return DeleteRouterUseCaseSuccess(router=deleted_router)
            case RouterNotFoundError(id=not_found_id):
                return RouterNotFoundError(id=not_found_id)
