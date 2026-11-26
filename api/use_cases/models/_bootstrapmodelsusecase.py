from collections import Counter
from dataclasses import dataclass
import logging

from api.domain.model.errors import (
    InconsistentModelMaxContextLengthError,
    InconsistentModelQosLimitError,
    InconsistentModelVectorSizeError,
    ModelNotFoundError,
)
from api.domain.provider import ProviderRepository
from api.domain.provider.entities import HostingZone, Provider, ProviderType
from api.domain.provider.errors import ProviderAlreadyExistsError, ProviderInvalidResponseError, ProviderNotReachableError
from api.domain.router import RouterRepository
from api.domain.router.entities import RouterType
from api.domain.router.errors import RouterNameAlreadyExistsError
from api.use_cases.services import ProviderCapabilitiesProbe

logger = logging.getLogger(__name__)


@dataclass
class ProviderToCreate:
    type: ProviderType
    url: str
    key: str | None
    timeout: int
    qos_limit: int | None
    model_name: str
    model_hosting_zone: HostingZone
    model_total_params: int
    model_active_params: int


@dataclass
class RouterToCreate:
    name: str
    type: RouterType
    aliases: list[str]
    qos_retries_before_reject: int | None
    cost_prompt_tokens: float
    cost_completion_tokens: float
    providers: list[ProviderToCreate]


@dataclass
class BootstrapModelsCommand:
    routers_to_create: list[RouterToCreate]
    bootstrap_admin_user_id: int


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
    | InconsistentModelQosLimitError
    | ModelNotFoundError
    | ProviderAlreadyExistsError
    | ProviderNotReachableError
    | ProviderInvalidResponseError
    | RouterNameAlreadyExistsError
)


class BootstrapModelsUseCase:
    def __init__(
        self,
        router_repository: RouterRepository,
        provider_repository: ProviderRepository,
        provider_capabilities_probe: ProviderCapabilitiesProbe,
    ):
        self.router_repository = router_repository
        self.provider_repository = provider_repository
        self.provider_capabilities_probe = provider_capabilities_probe

    async def execute(self, command: BootstrapModelsCommand) -> BootstrapModelsUseCaseResult:
        routers = await self.router_repository.get_all_routers()
        if len(routers) > 0:
            return BootstrapModelsUseCaseSkipped(number_of_routers=len(routers))

        # check if no duplicates router name or alias
        router_to_create_names = []
        for i, router_to_create in enumerate(command.routers_to_create):
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

        for router_to_create in command.routers_to_create:
            router = await self.router_repository.create_router(
                name=router_to_create.name,
                router_type=router_to_create.type,
                qos_retries_before_reject=router_to_create.qos_retries_before_reject,
                cost_prompt_tokens=router_to_create.cost_prompt_tokens,
                cost_completion_tokens=router_to_create.cost_completion_tokens,
                user_id=command.bootstrap_admin_user_id,
                aliases=router_to_create.aliases,
            )

            for provider_to_create in router_to_create.providers:
                result = await self.provider_capabilities_probe.get_capabilities(
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
                    case ProviderInvalidResponseError() as error:
                        await self.router_repository.delete_all_routers()
                        return error
                    case provider_capabilities:
                        pass

                inconsistency = router.check_new_provider(capabilities=provider_capabilities, qos_limit=provider_to_create.qos_limit)
                if inconsistency is not None:
                    await self.router_repository.delete_all_routers()
                    return inconsistency

                result = await self.provider_repository.create_provider(
                    router_id=router.id,
                    user_id=command.bootstrap_admin_user_id,
                    provider_type=provider_to_create.type,
                    url=provider_to_create.url,
                    key=provider_to_create.key,
                    timeout=provider_to_create.timeout,
                    qos_limit=provider_to_create.qos_limit,
                    model_name=provider_to_create.model_name,
                    model_hosting_zone=provider_to_create.model_hosting_zone,
                    model_total_params=provider_to_create.model_total_params,
                    model_active_params=provider_to_create.model_active_params,
                    max_context_length=provider_capabilities.max_context_length,
                    vector_size=provider_capabilities.vector_size,
                )
                match result:
                    case Provider() as provider:
                        router = router.with_provider(provider)
                    case ProviderAlreadyExistsError() as error:
                        return error

        return BootstrapModelsUseCaseSuccess(number_of_routers=len(command.routers_to_create))
