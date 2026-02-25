from dataclasses import dataclass

from api.domain.router import RouterRepository
from api.domain.router.entities import Router
from api.domain.router.errors import RouterNotFoundError
from api.domain.userinfo import UserInfoRepository
from api.domain.userinfo.errors import UserIsNotAdminError


@dataclass
class GetOneRouterCommand:
    user_id: int
    router_id: int


@dataclass
class GetOneRouterUseCaseSuccess:
    router: Router


type GetOneRouterUseCaseResult = GetOneRouterUseCaseSuccess | RouterNotFoundError | UserIsNotAdminError


class GetOneRouterUseCase:
    def __init__(self, router_repository: RouterRepository, user_info_repository: UserInfoRepository):
        self.router_repository = router_repository
        self.user_info_repository = user_info_repository

    async def execute(
        self,
        command: GetOneRouterCommand,
    ) -> GetOneRouterUseCaseResult:
        user_info = await self.user_info_repository.get_user_info(user_id=command.user_id)

        if not user_info.is_admin:
            return UserIsNotAdminError()

        router = await self.router_repository.get_router_by_id(command.router_id)

        if not router:
            return RouterNotFoundError(command.router_id)
        return GetOneRouterUseCaseSuccess(router=router)
