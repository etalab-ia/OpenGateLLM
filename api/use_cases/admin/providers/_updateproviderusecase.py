from dataclasses import dataclass

from api.domain.model.errors import InconsistentModelMaxContextLengthError, InconsistentModelQosLimitError, InconsistentModelVectorSizeError
from api.domain.provider import ProviderRepository, TokenizerRegistry
from api.domain.provider.entities import HostingZone, Provider
from api.domain.provider.errors import (
    InvalidProviderTypeError,
    ProviderAlreadyExistsError,
    ProviderNotFoundError,
    TokenizerNotLoadableError,
)
from api.domain.router import RouterRepository
from api.domain.router.entities import Router
from api.domain.router.errors import RouterNotFoundError


@dataclass
class UpdateProviderCommand:
    provider_id: int
    router_id: int
    timeout: int
    model_hosting_zone: HostingZone
    model_total_params: int
    model_active_params: int
    qos_limit: int | None
    tokenizer_name: str
    hf_token: str | None = None


@dataclass
class UpdateProviderUseCaseSuccess:
    provider: Provider


type UpdateProviderUseCaseResult = (
    UpdateProviderUseCaseSuccess
    | InvalidProviderTypeError
    | InconsistentModelMaxContextLengthError
    | InconsistentModelVectorSizeError
    | InconsistentModelQosLimitError
    | RouterNotFoundError
    | ProviderAlreadyExistsError
    | ProviderNotFoundError
    | TokenizerNotLoadableError
)


class UpdateProviderUseCase:
    def __init__(
        self,
        router_repository: RouterRepository,
        provider_repository: ProviderRepository,
        tokenizer_registry: TokenizerRegistry,
    ):
        self.router_repository = router_repository
        self.provider_repository = provider_repository
        self.tokenizer_registry = tokenizer_registry

    async def execute(self, command: UpdateProviderCommand) -> UpdateProviderUseCaseResult:
        match await self.provider_repository.get_one_provider(provider_id=command.provider_id):
            case ProviderNotFoundError() as error:
                return error
            case Provider() as existing_provider:
                pass

        hf_token = command.hf_token if command.hf_token is not None else existing_provider.hf_token
        match await self.tokenizer_registry.get(tokenizer_name=command.tokenizer_name, hf_token=hf_token):
            case TokenizerNotLoadableError() as error:
                return error

        provider_to_persist = (
            existing_provider.with_router_id(command.router_id)
            .with_timeout(command.timeout)
            .with_tokenizer_name(command.tokenizer_name)
            .with_hf_token(hf_token)
            .with_model_hosting_zone(command.model_hosting_zone)
            .with_model_total_params(command.model_total_params)
            .with_model_active_params(command.model_active_params)
            .with_qos_limit(command.qos_limit)
        )

        if existing_provider == provider_to_persist:
            return UpdateProviderUseCaseSuccess(existing_provider)

        match await self.router_repository.lock_and_get_router_by_id(router_id=command.router_id):
            case RouterNotFoundError() as error:
                return error
            case Router() as target_router:
                pass

        inconsistency = target_router.check_provider(provider_to_persist)
        if inconsistency is not None:
            return inconsistency

        result = await self.provider_repository.update_provider(provider_to_persist)

        match result:
            case Provider() as updated_provider:
                return UpdateProviderUseCaseSuccess(provider=updated_provider)
            case error:
                return error
