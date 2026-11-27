from dataclasses import dataclass

from api.domain.model.errors import (
    InconsistentModelMaxContextLengthError,
    InconsistentModelQosLimitError,
    InconsistentModelVectorSizeError,
    ModelNotFoundError,
)
from api.domain.provider import ProviderRepository
from api.domain.provider.entities import HostingZone, Provider, ProviderType
from api.domain.provider.errors import (
    InvalidProviderTypeError,
    ProviderAlreadyExistsError,
    ProviderInvalidResponseError,
    ProviderNotReachableError,
)
from api.domain.router import RouterRepository
from api.domain.router.entities import Router
from api.domain.router.errors import RouterNotFoundError
from api.use_cases.services import ProviderCapabilitiesProbe


@dataclass
class CreateProviderCommand:
    user_id: int
    router_id: int
    provider_type: ProviderType
    url: str
    key: str | None
    timeout: int
    model_name: str
    model_hosting_zone: HostingZone
    model_total_params: int
    model_active_params: int
    qos_limit: int | None = None


@dataclass
class CreateProviderUseCaseSuccess:
    provider: Provider


type CreateProviderUseCaseResult = (
    CreateProviderUseCaseSuccess
    | InvalidProviderTypeError
    | ProviderNotReachableError
    | ProviderInvalidResponseError
    | ModelNotFoundError
    | InconsistentModelMaxContextLengthError
    | InconsistentModelVectorSizeError
    | InconsistentModelQosLimitError
    | RouterNotFoundError
    | ProviderAlreadyExistsError
)


class CreateProviderUseCase:
    def __init__(
        self,
        router_repository: RouterRepository,
        provider_repository: ProviderRepository,
        provider_capabilities_probe: ProviderCapabilitiesProbe,
    ):
        self.router_repository = router_repository
        self.provider_repository = provider_repository
        self.provider_capabilities_probe = provider_capabilities_probe

    async def execute(self, command: CreateProviderCommand) -> CreateProviderUseCaseResult:
        match await self.router_repository.lock_and_get_router_by_id(router_id=command.router_id):
            case RouterNotFoundError() as error:
                return error
            case Router() as router:
                pass

        if not router.is_compatible_with_provider_type(command.provider_type):
            return InvalidProviderTypeError(provider_type=command.provider_type.value, router_type=router.type.value)

        result = await self.provider_capabilities_probe.get_capabilities(
            router_type=router.type,
            provider_type=command.provider_type,
            url=command.url,
            key=command.key,
            timeout=command.timeout,
            model_name=command.model_name,
        )
        match result:
            case ProviderNotReachableError() as error:
                return error
            case ModelNotFoundError() as error:
                return error
            case ProviderInvalidResponseError() as error:
                return error
            case provider_capabilities:
                pass

        inconsistency = router.check_new_provider(capabilities=provider_capabilities, qos_limit=command.qos_limit)
        if inconsistency is not None:
            return inconsistency

        result = await self.provider_repository.create_provider(
            router_id=command.router_id,
            user_id=command.user_id,
            provider_type=command.provider_type,
            url=command.url,
            key=command.key,
            timeout=command.timeout,
            qos_limit=command.qos_limit,
            model_name=command.model_name,
            tokenizer_name=command.model_name,
            hf_token=None,
            model_hosting_zone=command.model_hosting_zone,
            model_total_params=command.model_total_params,
            model_active_params=command.model_active_params,
            max_context_length=provider_capabilities.max_context_length,
            vector_size=provider_capabilities.vector_size,
        )

        match result:
            case Provider() as provider:
                return CreateProviderUseCaseSuccess(provider)
            case error:
                return error
