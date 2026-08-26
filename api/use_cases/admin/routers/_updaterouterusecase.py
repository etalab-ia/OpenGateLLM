from dataclasses import dataclass

from api.domain.model.entities import ModelType as RouterType
from api.domain.router import RouterRepository
from api.domain.router.entities import Router, RouterLoadBalancingStrategy
from api.domain.router.errors import RouterAliasAlreadyExistsError, RouterNameAlreadyExistsError, RouterNotFoundError


@dataclass
class UpdateRouterCommand:
    router_id: int
    name: str
    router_type: RouterType
    aliases: list[str]
    load_balancing_strategy: RouterLoadBalancingStrategy
    cost_prompt_tokens: float
    cost_completion_tokens: float


@dataclass
class UpdateRouterUseCaseSuccess:
    router: Router


type UpdateRouterUseCaseResult = UpdateRouterUseCaseSuccess | RouterNameAlreadyExistsError | RouterAliasAlreadyExistsError | RouterNotFoundError


class UpdateRouterUseCase:
    def __init__(self, router_repository: RouterRepository):
        self.router_repository = router_repository

    async def execute(self, command: UpdateRouterCommand) -> UpdateRouterUseCaseResult:
        router = await self.router_repository.get_router_by_id(router_id=command.router_id)
        if isinstance(router, RouterNotFoundError):
            return RouterNotFoundError(id=command.router_id)

        if command.aliases:
            existing_aliases = await self.router_repository.get_aliases()
            conflicting_aliases = set(command.aliases) & (set(existing_aliases) - set(router.aliases or []))
            if conflicting_aliases:
                return RouterAliasAlreadyExistsError(aliases=list(conflicting_aliases))

        router_to_persist = (
            router.with_name(command.name)
            .with_type(command.router_type)
            .with_load_balancing_strategy(command.load_balancing_strategy)
            .with_cost_prompt_tokens(command.cost_prompt_tokens)
            .with_cost_completion_tokens(command.cost_completion_tokens)
            .with_aliases(command.aliases)
        )

        if router_to_persist == router:
            return UpdateRouterUseCaseSuccess(router=router)

        result = await self.router_repository.update_router(router=router_to_persist)

        match result:
            case Router() as updated_router:
                return UpdateRouterUseCaseSuccess(router=updated_router)
            case error:
                return error
