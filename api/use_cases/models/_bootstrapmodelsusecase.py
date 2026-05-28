from collections import Counter
from dataclasses import dataclass
import logging

from api.domain.model.errors import InconsistentModelMaxContextLengthError, InconsistentModelVectorSizeError, ModelNotFoundError
from api.domain.provider import ProviderGateway, ProviderRepository
from api.domain.provider.errors import ProviderAlreadyExistsError, ProviderNotReachableError
from api.domain.router import RouterRepository
from api.domain.router.errors import RouterNameAlreadyExistsError
from api.schemas.core.configuration import Model as ModelConfiguration

logger = logging.getLogger(__name__)


@dataclass
class BootstrapModelsUseCaseSuccess:
    number_of_routers: int


@dataclass
class BootstrapModelsUseCaseSkipped:
    number_of_routers: int


type BootstrapModelsUseCaseResult = (
    BootstrapModelsUseCaseSuccess
    | BootstrapModelsUseCaseSkipped
    | InconsistentModelVectorSizeError
    | InconsistentModelMaxContextLengthError
    | ModelNotFoundError
    | ProviderAlreadyExistsError
    | ProviderNotReachableError
    | RouterNameAlreadyExistsError
)


class BootstrapModelsUseCase:
    def __init__(self, router_repository: RouterRepository, provider_repository: ProviderRepository, provider_gateway: ProviderGateway):
        self.router_repository = router_repository
        self.provider_repository = provider_repository
        self.provider_gateway = provider_gateway

    async def execute(
        self,
        routers_to_create: list[ModelConfiguration],
        bootstrap_admin_user_id: int,
    ) -> BootstrapModelsUseCaseResult:
        routers = await self.router_repository.get_all_routers()
        if len(routers) > 0:
            return BootstrapModelsUseCaseSkipped(number_of_routers=len(routers))

        # check if no duplicates router name or alias
        router_to_create_names = []
        for i, router_to_create in enumerate(routers_to_create):
            router_to_create_names.append(router_to_create.name)
            router_to_create_names.extend(router_to_create.aliases)

            provider_to_create_urls_and_model_names = []
            for provider_to_create in router_to_create.providers:
                provider_to_create_urls_and_model_names.append((provider_to_create.url, provider_to_create.model_name))

            duplicates = [val for val, count in Counter(provider_to_create_urls_and_model_names).items() if count > 1]
            if duplicates:
                url, model_name = duplicates[0]
                return ProviderAlreadyExistsError(url=url, model_name=model_name, router_id=i)

        duplicates = [val for val, count in Counter(router_to_create_names).items() if count > 1]
        if duplicates:
            return RouterNameAlreadyExistsError(name=duplicates[0])

        for router_to_create in routers_to_create:
            router = await self.router_repository.create_router(
                name=router_to_create.name,
                router_type=router_to_create.type,
                load_balancing_strategy=router_to_create.load_balancing_strategy,
                cost_prompt_tokens=router_to_create.cost_prompt_tokens,
                cost_completion_tokens=router_to_create.cost_completion_tokens,
                user_id=bootstrap_admin_user_id,
                aliases=router_to_create.aliases,
            )

            for i, provider_to_create in enumerate(router_to_create.providers):
                result = await self.provider_gateway.get_capabilities(
                    router_type=router.type,
                    provider_type=provider_to_create.type,
                    url=provider_to_create.url,
                    key=provider_to_create.key,
                    timeout=provider_to_create.timeout,
                    model_name=provider_to_create.model_name,
                )
                match result:
                    case ProviderNotReachableError() as error:
                        await self.router_repository.delete_all_routers()
                        return error
                    case ModelNotFoundError() as error:
                        await self.router_repository.delete_all_routers()
                        return error
                    case provider_capabilities:
                        pass

                max_context_length = provider_capabilities.max_context_length
                vector_size = provider_capabilities.vector_size

                if i > 0 and not router.max_context_length_is_consistent(max_context_length):
                    await self.router_repository.delete_all_routers()
                    return InconsistentModelMaxContextLengthError(
                        actual_max_context_length=max_context_length,
                        expected_max_context_length=router.max_context_length,
                        router_name=router.name,
                    )

                if i > 0 and not router.vector_size_is_consistent(vector_size):
                    await self.router_repository.delete_all_routers()
                    return InconsistentModelVectorSizeError(
                        actual_vector_size=vector_size,
                        expected_vector_size=router.vector_size,
                        router_name=router.name,
                    )

                result = await self.provider_repository.create_provider(
                    router_id=router.id,
                    user_id=bootstrap_admin_user_id,
                    provider_type=provider_to_create.type,
                    url=provider_to_create.url,
                    key=provider_to_create.key,
                    timeout=provider_to_create.timeout,
                    model_name=provider_to_create.model_name,
                    model_hosting_zone=provider_to_create.model_hosting_zone,
                    model_total_params=provider_to_create.model_total_params,
                    model_active_params=provider_to_create.model_active_params,
                    qos_metric=provider_to_create.qos_metric,
                    qos_limit=provider_to_create.qos_limit,
                    max_context_length=max_context_length,
                    vector_size=vector_size,
                )

        return BootstrapModelsUseCaseSuccess(number_of_routers=len(routers_to_create))
