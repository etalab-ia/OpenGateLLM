from dataclasses import dataclass

from api.domain.model.errors import InconsistentModelMaxContextLengthError, InconsistentModelVectorSizeError, ModelNotFoundError
from api.domain.provider import ProviderCapabilitiesRepository, ProviderRepository
from api.domain.provider.entities import BasicAuth, HostingZone, Metric, Provider, ProviderType
from api.domain.provider.errors import InvalidProviderTypeError, ProviderAlreadyExistsError, ProviderNotReachableError
from api.domain.router import RouterRepository
from api.domain.router.errors import RouterNotFoundError


@dataclass
class CreateProviderCommand:
    user_id: int
    router_id: int
    provider_type: ProviderType
    url: str
    key: str | None
    basic_auth: BasicAuth | None
    timeout: int
    model_name: str
    model_hosting_zone: HostingZone
    model_total_params: int
    model_active_params: int
    qos_metric: Metric | None
    qos_limit: float | None


@dataclass
class CreateProviderUseCaseSuccess:
    provider: Provider


type CreateProviderUseCaseResult = (
    CreateProviderUseCaseSuccess
    | InvalidProviderTypeError
    | ProviderNotReachableError
    | ModelNotFoundError
    | InconsistentModelMaxContextLengthError
    | InconsistentModelVectorSizeError
    | RouterNotFoundError
    | ProviderAlreadyExistsError
)


class CreateProviderUseCase:
    def __init__(
        self,
        router_repository: RouterRepository,
        provider_repository: ProviderRepository,
        provider_capabilities_repository: ProviderCapabilitiesRepository,
    ):
        self.router_repository = router_repository
        self.provider_repository = provider_repository
        self.provider_capabilities_repository = provider_capabilities_repository

    async def execute(self, command: CreateProviderCommand) -> CreateProviderUseCaseResult:
        router = await self.router_repository.get_router_by_id(router_id=command.router_id)
        if router is None:
            return RouterNotFoundError(id=command.router_id)

        if not command.provider_type.is_compatible_with(router_type=router.type):
            return InvalidProviderTypeError(provider_type=command.provider_type.value, router_type=router.type.value)

        result = await self.provider_capabilities_repository.get_provider_capabilities(
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
            case provider_capabilities:
                pass

        max_context_length = provider_capabilities.max_context_length
        vector_size = provider_capabilities.vector_size

        if router.providers > 0 and not router.vector_size_is_consistent(vector_size):
            return InconsistentModelVectorSizeError(
                actual_vector_size=vector_size,
                expected_vector_size=router.vector_size,
                router_name=router.name,
            )
        if router.providers > 0 and not router.max_context_length_is_consistent(max_context_length):
            return InconsistentModelMaxContextLengthError(
                actual_max_context_length=max_context_length,
                expected_max_context_length=router.max_context_length,
                router_name=router.name,
            )

        result = await self.provider_repository.create_provider(
            router_id=command.router_id,
            user_id=command.user_id,
            provider_type=command.provider_type,
            url=command.url,
            key=command.key,
            basic_auth=command.basic_auth,
            timeout=command.timeout,
            model_name=command.model_name,
            model_hosting_zone=command.model_hosting_zone,
            model_total_params=command.model_total_params,
            model_active_params=command.model_active_params,
            qos_metric=command.qos_metric,
            qos_limit=command.qos_limit,
            max_context_length=max_context_length,
            vector_size=vector_size,
        )

        match result:
            case Provider() as provider:
                return CreateProviderUseCaseSuccess(provider)
            case error:
                return error
