from dataclasses import dataclass

from api.domain.model.entities import ModelType as RouterType
from api.domain.router import RouterRepository
from api.domain.router.entities import Router, RouterLoadBalancingStrategy
from api.domain.router.errors import RouterAliasAlreadyExistsError, RouterNameAlreadyExistsError
from api.domain.user import UserWithRoleQuery
from api.domain.user.errors import UserExpiredError, UserIsNotAdminError


@dataclass
class CreateRouterCommand:
    user_id: int
    name: str
    router_type: RouterType
    aliases: list[str]
    load_balancing_strategy: RouterLoadBalancingStrategy
    cost_prompt_tokens: float
    cost_completion_tokens: float


@dataclass
class CreateRouterUseCaseSuccess:
    router: Router


type CreateRouterUseCaseResult = (
    CreateRouterUseCaseSuccess | RouterNameAlreadyExistsError | RouterAliasAlreadyExistsError | UserExpiredError | UserIsNotAdminError
)


class CreateRouterUseCase:
    def __init__(self, router_repository: RouterRepository, user_with_role_query: UserWithRoleQuery):
        self.router_repository = router_repository
        self.user_with_role_query = user_with_role_query

    async def execute(
        self,
        command: CreateRouterCommand,
    ) -> CreateRouterUseCaseResult:
        user = await self.user_with_role_query.get_user_with_role_by_id(user_id=command.user_id)

        if user.has_expired:
            return UserExpiredError()

        if not user.is_admin:
            return UserIsNotAdminError()

        result = await self.router_repository.create_router(
            name=command.name,
            router_type=command.router_type,
            load_balancing_strategy=command.load_balancing_strategy,
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
