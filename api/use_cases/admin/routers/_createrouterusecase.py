from dataclasses import dataclass

from api.domain.router import RouterRepository
from api.domain.router.entities import Router, RouterLoadBalancingStrategy, RouterQosMetric, RouterQosMode, RouterType
from api.domain.router.errors import RouterAliasAlreadyExistsError, RouterNameAlreadyExistsError


@dataclass
class CreateRouterCommand:
    user_id: int
    name: str
    router_type: RouterType
    aliases: list[str]
    load_balancing_strategy: RouterLoadBalancingStrategy
    qos_mode: RouterQosMode
    qos_retry: int
    qos_metric: RouterQosMetric
    qos_health_thresholds: list[float]
    cost_prompt_tokens: float
    cost_completion_tokens: float


@dataclass
class CreateRouterUseCaseSuccess:
    router: Router


type CreateRouterUseCaseResult = CreateRouterUseCaseSuccess | RouterNameAlreadyExistsError | RouterAliasAlreadyExistsError


class CreateRouterUseCase:
    def __init__(self, router_repository: RouterRepository):
        self.router_repository = router_repository

    async def execute(self, command: CreateRouterCommand) -> CreateRouterUseCaseResult:
        result = await self.router_repository.create_router(
            name=command.name,
            router_type=command.router_type,
            load_balancing_strategy=command.load_balancing_strategy,
            qos_mode=command.qos_mode,
            qos_retry=command.qos_retry,
            qos_metric=command.qos_metric,
            qos_health_thresholds=command.qos_health_thresholds,
            cost_prompt_tokens=command.cost_prompt_tokens,
            cost_completion_tokens=command.cost_completion_tokens,
            user_id=command.user_id,
            aliases=command.aliases,
        )

        match result:
            case Router() as router:
                return CreateRouterUseCaseSuccess(router)
            case error:
                return error
