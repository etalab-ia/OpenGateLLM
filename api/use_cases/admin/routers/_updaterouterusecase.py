from dataclasses import dataclass

from api.domain.model import ModelType as RouterType
from api.domain.router import RouterRepository
from api.domain.router.entities import Router, RouterLoadBalancingStrategy
from api.domain.router.errors import RouterAliasAlreadyExistsError, RouterNameAlreadyExistsError, RouterNotFoundError
from api.domain.userinfo import UserInfoRepository
from api.domain.userinfo.errors import UserIsNotAdminError


@dataclass
class UpdateRouterCommand:
    user_id: int
    router_id: int
    name: str | None = None
    router_type: RouterType | None = None
    aliases: list[str] | None = None
    load_balancing_strategy: RouterLoadBalancingStrategy | None = None
    cost_prompt_tokens: float | None = None
    cost_completion_tokens: float | None = None


@dataclass
class UpdateRouterUseCaseSuccess:
    router: Router


type UpdateRouterUseCaseResult = (
    UpdateRouterUseCaseSuccess | RouterNameAlreadyExistsError | RouterAliasAlreadyExistsError | UserIsNotAdminError | RouterNotFoundError
)


class UpdateRouterUseCase:
    def __init__(self, router_repository: RouterRepository, user_info_repository: UserInfoRepository):
        self.router_repository = router_repository
        self.user_info_repository = user_info_repository

    async def execute(
        self,
        command: UpdateRouterCommand,
    ) -> UpdateRouterUseCaseResult:
        user_info = await self.user_info_repository.get_user_info(user_id=command.user_id)

        if not user_info.is_admin:
            return UserIsNotAdminError()

        router = await self.router_repository.get_router_by_id(router_id=command.router_id)
        if router is None:
            return RouterNotFoundError(router_id=command.router_id)

        if command.aliases:
            existing_aliases = await self.router_repository.get_aliases()
            conflicting_aliases = set(command.aliases) & (set(existing_aliases) - set(router.aliases or []))
            if conflicting_aliases:
                return RouterAliasAlreadyExistsError(aliases=list(conflicting_aliases))

        router_to_persist = router
        if command.name is not None:
            router_to_persist = router_to_persist.with_name(command.name)
        if command.router_type is not None:
            router_to_persist = router_to_persist.with_type(command.router_type)
        if command.load_balancing_strategy is not None:
            router_to_persist = router_to_persist.with_load_balancing_strategy(command.load_balancing_strategy)
        if command.cost_prompt_tokens is not None:
            router_to_persist = router_to_persist.with_cost_prompt_tokens(command.cost_prompt_tokens)
        if command.cost_completion_tokens is not None:
            router_to_persist = router_to_persist.with_cost_completion_tokens(command.cost_completion_tokens)
        if command.aliases is not None:
            router_to_persist = router_to_persist.with_aliases(command.aliases)

        if router_to_persist == router:
            return UpdateRouterUseCaseSuccess(router=router)

        result = await self.router_repository.update_router(router_to_update=router_to_persist)

        match result:
            case Router() as updated_router:
                return UpdateRouterUseCaseSuccess(router=updated_router)
            case error:
                return error
