from dataclasses import dataclass

from api.domain.router import RouterAuthorization, RouterRepository
from api.domain.router.entities import Router, RouterType
from api.domain.router.errors import RouterAliasAlreadyExistsError, RouterNameAlreadyExistsError, RouterNotFoundError, UserCannotUpdateRouterError


@dataclass
class UpdateRouterCommand:
    authenticated_user_id: int
    router_id: int
    name: str
    router_type: RouterType
    aliases: list[str]
    cost_prompt_tokens: float
    cost_completion_tokens: float
    qos_retries_before_reject: int | None


@dataclass
class UpdateRouterUseCaseSuccess:
    router: Router


type UpdateRouterUseCaseResult = (
    UpdateRouterUseCaseSuccess | RouterNameAlreadyExistsError | RouterAliasAlreadyExistsError | RouterNotFoundError | UserCannotUpdateRouterError
)


class UpdateRouterUseCase:
    def __init__(self, router_repository: RouterRepository, router_authorization: RouterAuthorization):
        self.router_repository = router_repository
        self.router_authorization = router_authorization

    async def execute(self, command: UpdateRouterCommand) -> UpdateRouterUseCaseResult:
        is_authorized = await self.router_authorization.can_update_router(user_id=command.authenticated_user_id, router_id=command.router_id)

        if not is_authorized:
            return UserCannotUpdateRouterError(user_id=command.authenticated_user_id)

        router = await self.router_repository.get_router_by_id(router_id=command.router_id)
        if isinstance(router, RouterNotFoundError):
            return RouterNotFoundError(id=command.router_id)

        if command.aliases:
            existing_aliases = await self.router_repository.get_aliases()
            conflicting_aliases = set(command.aliases) & (set(existing_aliases) - set(router.aliases))
            if conflicting_aliases:
                return RouterAliasAlreadyExistsError(aliases=list(conflicting_aliases))

        router_to_persist = (
            router.with_name(command.name)
            .with_type(command.router_type)
            .with_cost_prompt_tokens(command.cost_prompt_tokens)
            .with_cost_completion_tokens(command.cost_completion_tokens)
            .with_qos_retries_before_reject(command.qos_retries_before_reject)
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
