from dataclasses import dataclass

from api.domain.model.errors import InconsistentModelMaxContextLengthError, InconsistentModelVectorSizeError
from api.domain.provider import ProviderRepository
from api.domain.provider.entities import HostingZone, Metric, Provider
from api.domain.provider.errors import InvalidProviderTypeError, ProviderAlreadyExistsError, ProviderNotFoundError
from api.domain.router import RouterRepository
from api.domain.router.errors import RouterNotFoundError


@dataclass
class UpdateProviderCommand:
    provider_id: int
    router_id: int | None
    timeout: int | None
    model_hosting_zone: HostingZone | None
    model_total_params: int | None
    model_active_params: int | None
    qos_metric: Metric | None
    qos_limit: float | None


@dataclass
class UpdateProviderUseCaseSuccess:
    provider: Provider


type UpdateProviderUseCaseResult = (
    UpdateProviderUseCaseSuccess
    | InvalidProviderTypeError
    | InconsistentModelMaxContextLengthError
    | InconsistentModelVectorSizeError
    | RouterNotFoundError
    | ProviderAlreadyExistsError
    | ProviderNotFoundError
)


class UpdateProviderUseCase:
    def __init__(
        self,
        router_repository: RouterRepository,
        provider_repository: ProviderRepository,
    ):
        self.router_repository = router_repository
        self.provider_repository = provider_repository

    async def execute(self, command: UpdateProviderCommand) -> UpdateProviderUseCaseResult:
        existing_provider = await self.provider_repository.get_one_provider(provider_id=command.provider_id)
        if isinstance(existing_provider, ProviderNotFoundError):
            return existing_provider

        provider_to_persist = existing_provider
        if command.router_id is not None:
            new_router = await self.router_repository.get_router_by_id(router_id=command.router_id)
            if isinstance(new_router, RouterNotFoundError):
                return new_router
            if not existing_provider.is_compatible_with(new_router):
                return InvalidProviderTypeError(provider_type=existing_provider.type.value, router_type=new_router.type.value)

            # all providers of a router must expose the same capabilities: compare with one of the providers already attached to the target router
            new_router_providers = await self.provider_repository.get_all_providers_of_router(router_id=new_router.id)
            reference_provider = next((provider for provider in new_router_providers if provider.id != existing_provider.id), None)
            if reference_provider is not None:
                if reference_provider.vector_size != existing_provider.vector_size:
                    return InconsistentModelVectorSizeError(
                        actual_vector_size=existing_provider.vector_size,
                        expected_vector_size=reference_provider.vector_size,
                        router_name=new_router.name,
                    )
                if reference_provider.max_context_length != existing_provider.max_context_length:
                    return InconsistentModelMaxContextLengthError(
                        actual_max_context_length=existing_provider.max_context_length,
                        expected_max_context_length=reference_provider.max_context_length,
                        router_name=new_router.name,
                    )
            provider_to_persist = existing_provider.with_router_id(new_router.id)

        if command.timeout is not None:
            provider_to_persist = provider_to_persist.with_timeout(command.timeout)
        if command.model_hosting_zone is not None:
            provider_to_persist = provider_to_persist.with_model_hosting_zone(command.model_hosting_zone)
        if command.model_total_params is not None:
            provider_to_persist = provider_to_persist.with_model_total_params(command.model_total_params)
        if command.model_active_params is not None:
            provider_to_persist = provider_to_persist.with_model_active_params(command.model_active_params)
        if command.qos_metric is not None:
            provider_to_persist = provider_to_persist.with_qos_metric(command.qos_metric)
        if command.qos_limit is not None:
            provider_to_persist = provider_to_persist.with_qos_limit(command.qos_limit)

        if existing_provider == provider_to_persist:
            return UpdateProviderUseCaseSuccess(existing_provider)

        result = await self.provider_repository.update_provider(provider_to_persist)

        match result:
            case Provider() as updated_provider:
                return UpdateProviderUseCaseSuccess(provider=updated_provider)
            case error:
                return error
