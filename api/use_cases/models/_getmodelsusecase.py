from api.domain.router import RouterRepository
from api.domain.router.entities import Router
from api.domain.userinfo import UserInfoRepository


class GetModelsUseCase:
    def __init__(self, user_id: int, router_repository: RouterRepository, user_info_repository: UserInfoRepository):
        self.user_id = user_id
        self.router_repository = router_repository
        self.user_info_repository = user_info_repository

    async def execute(self, name: str | None = None) -> list[Router]:
        user_info = await self.user_info_repository.get_user_info(user_id=self.user_id)

        models = await self.router_repository.get_all_models(name=name, user_info=user_info)

        return models
