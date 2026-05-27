from dataclasses import dataclass

from api.domain.router import RouterRepository
from api.domain.router.entities import Router
from api.domain.router.errors import RouterNotFoundError
from api.domain.user import UserWithRoleQuery
from api.domain.user.errors import UserExpiredError, UserIsNotAdminError


@dataclass
class DeleteRouterCommand:
    user_id: int
    router_id: int


@dataclass
class DeleteRouterUseCaseSuccess:
    router: Router


type DeleteRouterUseCaseResult = DeleteRouterUseCaseSuccess | RouterNotFoundError | UserExpiredError | UserIsNotAdminError


class DeleteRouterUseCase:
    def __init__(self, router_repository: RouterRepository, user_with_role_query: UserWithRoleQuery):
        self.router_repository = router_repository
        self.user_with_role_query = user_with_role_query

    async def execute(
        self,
        command: DeleteRouterCommand,
    ) -> DeleteRouterUseCaseResult:
        user = await self.user_with_role_query.get_user_with_role_by_id(user_id=command.user_id)

        if user.has_expired:
            return UserExpiredError()

        if not user.is_admin:
            return UserIsNotAdminError()

        result = await self.router_repository.delete_router(command.router_id)

        match result:
            case Router() as deleted_router:
                return DeleteRouterUseCaseSuccess(router=deleted_router)
            case RouterNotFoundError(id=not_found_id):
                return RouterNotFoundError(id=not_found_id)
