from api.domain.router import RouterRepository
from api.domain.userinfo import UserInfoRepository


class CreateRouterUseCase:
    def __init__(self, router_repository: RouterRepository, user_info_repository: UserInfoRepository):
        self.router_repository = router_repository
        self.user_info_repository = user_info_repository

    async def execute(self, user_id: int, name, type, aliases, load_balancing_strategy, cost_prompt_tokens, cost_completion_tokens):
        user_info = await self.user_info_repository.get_user_info(user_id=user_id)

        router_id = await self.router_repository.create_router(
            name=name,
            type=type,
            aliases=aliases,
            load_balancing_strategy=load_balancing_strategy,
            cost_prompt_tokens=cost_prompt_tokens,
            cost_completion_tokens=cost_completion_tokens,
            user_id=user_info.id,
        )

        return router_id
