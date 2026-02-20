from dataclasses import dataclass

from api.domain.router import RouterRepository
from api.domain.router.entities import ModelType, Router, RouterLoadBalancingStrategy
from api.domain.router.errors import RouterAliasAlreadyExistsError, RouterNameAlreadyExistsError
from api.domain.userinfo import UserInfoRepository
from api.domain.userinfo.errors import InsufficientPermissionError


@dataclass
class CreateRouterUseCaseSuccess:
    router: Router


type CreateRouterUseCaseResult = (
    CreateRouterUseCaseSuccess | RouterNameAlreadyExistsError | RouterAliasAlreadyExistsError | InsufficientPermissionError
)


class CreateRouterUseCase:
    def __init__(self, router_repository: RouterRepository, user_info_repository: UserInfoRepository):
        self.router_repository = router_repository
        self.user_info_repository = user_info_repository

    async def execute(
        self,
        user_id: int,
        name: str,
        router_type: ModelType,
        aliases: list[str],
        load_balancing_strategy: RouterLoadBalancingStrategy,
        cost_prompt_tokens: float,
        cost_completion_tokens: float,
    ) -> CreateRouterUseCaseResult:
        user_info = await self.user_info_repository.get_user_info(user_id=user_id)

        if not user_info.is_admin:
            return InsufficientPermissionError()

        result = await self.router_repository.create_router(
            name=name,
            router_type=router_type,
            load_balancing_strategy=load_balancing_strategy,
            cost_prompt_tokens=cost_prompt_tokens,
            cost_completion_tokens=cost_completion_tokens,
            user_id=user_id,
            aliases=aliases,
        )

        match result:
            case Router() as router:
                return CreateRouterUseCaseSuccess(router)
            case error:
                return error
