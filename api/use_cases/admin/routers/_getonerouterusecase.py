from dataclasses import dataclass

from api.domain.router import RouterRepository
from api.domain.router.entities import Router
from api.domain.router.errors import RouterNotFoundError
from api.domain.user import UserWithRoleQuery
from api.domain.user.errors import UserExpiredError, UserIsNotAdminError


@dataclass
class GetOneRouterCommand:
    user_id: int
    router_id: int


@dataclass
class GetOneRouterUseCaseSuccess:
    router: Router


type GetOneRouterUseCaseResult = GetOneRouterUseCaseSuccess | RouterNotFoundError | UserExpiredError | UserIsNotAdminError


class GetOneRouterUseCase:
    def __init__(self, router_repository: RouterRepository, user_with_role_query: UserWithRoleQuery):
        self.router_repository = router_repository
        self.user_with_role_query = user_with_role_query

    async def execute(self, command: GetOneRouterCommand) -> GetOneRouterUseCaseResult:
        user = await self.user_with_role_query.get_user_with_role_by_id(user_id=command.user_id)

        if user.has_expired:
            return UserExpiredError()

        if not user.is_admin:
            return UserIsNotAdminError()

        router = await self.router_repository.get_router_by_id(command.router_id)

        if not router:
            return RouterNotFoundError(id=command.router_id)
        return GetOneRouterUseCaseSuccess(router=router)
