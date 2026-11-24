from dataclasses import dataclass

from api.domain.model import ModelTokenizerLoader
from api.domain.model.errors import ModelTokenizerNotLoadableError
from api.domain.router import RouterRepository
from api.domain.router.entities import Router, RouterType
from api.domain.router.errors import RouterAliasAlreadyExistsError, RouterNameAlreadyExistsError, RouterNotFoundError


@dataclass
class UpdateRouterCommand:
    router_id: int
    name: str
    router_type: RouterType
    aliases: list[str]
    cost_prompt_tokens: float
    cost_completion_tokens: float
    qos_retries_before_reject: int | None
    tokenizer: str | None


@dataclass
class UpdateRouterUseCaseSuccess:
    router: Router


type UpdateRouterUseCaseResult = (
    UpdateRouterUseCaseSuccess | RouterNameAlreadyExistsError | RouterAliasAlreadyExistsError | RouterNotFoundError | ModelTokenizerNotLoadableError
)


class UpdateRouterUseCase:
    def __init__(self, router_repository: RouterRepository, model_tokenizer_loader: ModelTokenizerLoader):
        self.router_repository = router_repository
        self.model_tokenizer_loader = model_tokenizer_loader

    async def execute(self, command: UpdateRouterCommand) -> UpdateRouterUseCaseResult:
        router = await self.router_repository.get_router_by_id(router_id=command.router_id)
        if isinstance(router, RouterNotFoundError):
            return RouterNotFoundError(id=command.router_id)

        if command.aliases:
            existing_aliases = await self.router_repository.get_aliases()
            conflicting_aliases = set(command.aliases) & (set(existing_aliases) - set(router.aliases))
            if conflicting_aliases:
                return RouterAliasAlreadyExistsError(aliases=list(conflicting_aliases))

        # only a tokenizer that changes is checked: an unrelated edit must not depend on the Hugging Face Hub
        if command.tokenizer is not None and command.tokenizer != router.tokenizer:
            tokenizer_result = await self.model_tokenizer_loader.load(command.tokenizer)
            if isinstance(tokenizer_result, ModelTokenizerNotLoadableError):
                return tokenizer_result

        router_to_persist = (
            router.with_name(command.name)
            .with_type(command.router_type)
            .with_cost_prompt_tokens(command.cost_prompt_tokens)
            .with_cost_completion_tokens(command.cost_completion_tokens)
            .with_qos_retries_before_reject(command.qos_retries_before_reject)
            .with_tokenizer(command.tokenizer)
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
