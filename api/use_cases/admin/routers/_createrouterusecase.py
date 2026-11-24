from dataclasses import dataclass

from api.domain.model import ModelTokenizerLoader
from api.domain.model.errors import ModelTokenizerNotLoadableError
from api.domain.router import RouterRepository
from api.domain.router.entities import Router, RouterType
from api.domain.router.errors import RouterAliasAlreadyExistsError, RouterNameAlreadyExistsError


@dataclass
class CreateRouterCommand:
    user_id: int
    name: str
    router_type: RouterType
    aliases: list[str]
    cost_prompt_tokens: float
    cost_completion_tokens: float
    qos_retries_before_reject: int | None = None
    tokenizer: str | None = None


@dataclass
class CreateRouterUseCaseSuccess:
    router: Router


type CreateRouterUseCaseResult = (
    CreateRouterUseCaseSuccess | RouterNameAlreadyExistsError | RouterAliasAlreadyExistsError | ModelTokenizerNotLoadableError
)


class CreateRouterUseCase:
    def __init__(self, router_repository: RouterRepository, model_tokenizer_loader: ModelTokenizerLoader):
        self.router_repository = router_repository
        self.model_tokenizer_loader = model_tokenizer_loader

    async def execute(self, command: CreateRouterCommand) -> CreateRouterUseCaseResult:
        if command.tokenizer is not None:
            tokenizer_result = await self.model_tokenizer_loader.load(command.tokenizer)
            if isinstance(tokenizer_result, ModelTokenizerNotLoadableError):
                return tokenizer_result

        result = await self.router_repository.create_router(
            name=command.name,
            router_type=command.router_type,
            qos_retries_before_reject=command.qos_retries_before_reject,
            tokenizer=command.tokenizer,
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
