from dataclasses import dataclass

from api.domain.router import RouterRepository
from api.domain.router.entities import Router
from api.domain.router.errors import RouterNotFoundError
from api.domain.userinfo import UserInfoRepository
from api.domain.userinfo.errors import UserIsNotAdminError


@dataclass
class DeleteRouterCommand:
    user_id: int
    router_id: int


@dataclass
class DeleteRouterUseCaseSuccess:
    router: Router


type DeleteRouterUseCaseResult = DeleteRouterUseCaseSuccess | RouterNotFoundError | UserIsNotAdminError


class DeleteRouterUseCase:
    def __init__(self, router_repository: RouterRepository, user_info_repository: UserInfoRepository):
        self.router_repository = router_repository
        self.user_info_repository = user_info_repository

    async def execute(
        self,
        command: DeleteRouterCommand,
    ) -> DeleteRouterUseCaseResult:
        user_info = await self.user_info_repository.get_user_info(user_id=command.user_id)

        if not user_info.is_admin:
            return UserIsNotAdminError()

        router = await self.router_repository.delete_router(command.router_id)

        if router is None:
            return RouterNotFoundError(command.router_id)
        return DeleteRouterUseCaseSuccess(router=router)
