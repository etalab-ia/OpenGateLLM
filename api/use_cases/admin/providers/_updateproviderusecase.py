from dataclasses import dataclass
import time

from api.domain.model.entities import Metric
from api.domain.model.errors import InconsistentModelMaxContextLengthError, InconsistentModelVectorSizeError
from api.domain.provider import ProviderRepository
from api.domain.provider.entities import Provider, ProviderCarbonFootprintZone
from api.domain.provider.errors import InvalidProviderTypeError, ProviderAlreadyExistsError, ProviderNotFoundError
from api.domain.router import RouterRepository
from api.domain.router.errors import RouterNotFoundError
from api.domain.user import UserWithRoleQuery
from api.domain.user.errors import UserExpiredError, UserIsNotAdminError


@dataclass
class UpdateProviderCommand:
    provider_id: int
    router_id: int | None
    user_id: int
    timeout: int | None
    model_hosting_zone: ProviderCarbonFootprintZone | None
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
    | UserExpiredError
    | UserIsNotAdminError
)


class UpdateProviderUseCase:
    def __init__(
        self,
        router_repository: RouterRepository,
        provider_repository: ProviderRepository,
        user_with_role_query: UserWithRoleQuery,
    ):
        self.router_repository = router_repository
        self.provider_repository = provider_repository
        self.user_with_role_query = user_with_role_query

    async def execute(self, command: UpdateProviderCommand) -> UpdateProviderUseCaseResult:
        user = await self.user_with_role_query.get_user_with_role_by_id(user_id=command.user_id)

        if user.expires is not None and user.expires < time.time():
            return UserExpiredError()

        if not user.is_admin:
            return UserIsNotAdminError()

        existing_provider = await self.provider_repository.get_one_provider(provider_id=command.provider_id)
        if isinstance(existing_provider, ProviderNotFoundError):
            return ProviderNotFoundError(id=command.provider_id)

        current_router = await self.router_repository.get_router_by_id(router_id=existing_provider.router_id)
        if isinstance(current_router, RouterNotFoundError):
            return RouterNotFoundError(id=existing_provider.router_id)

        provider_to_persist = existing_provider
        if command.router_id is not None:
            new_router = await self.router_repository.get_router_by_id(router_id=command.router_id)
            if new_router is None:
                return RouterNotFoundError(id=command.router_id)
            if not existing_provider.is_compatible_with(new_router):
                return InvalidProviderTypeError(provider_type=existing_provider.type.value, router_type=new_router.type.value)

            if new_router.providers > 0:
                if new_router.vector_size != current_router.vector_size:
                    return InconsistentModelVectorSizeError(
                        actual_vector_size=current_router.vector_size, expected_vector_size=new_router.vector_size, router_name=new_router.name
                    )
                if new_router.max_context_length != current_router.max_context_length:
                    return InconsistentModelMaxContextLengthError(
                        actual_max_context_length=current_router.max_context_length,
                        expected_max_context_length=new_router.max_context_length,
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
