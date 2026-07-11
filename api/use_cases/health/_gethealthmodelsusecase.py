from dataclasses import dataclass

from api.domain.model.entities import HealthStatus, ModelHealthStatus
from api.domain.provider import ProviderAdapter, ProviderAdapterBuilder, ProviderClient, ProviderMetricsLogger, ProviderRepository
from api.domain.provider.entities import ProviderFormattedResponse, ProviderOriginalRequest, ProviderOriginalResponse, ProviderType
from api.domain.provider.errors import ProviderAdapterValidationResponseError, UnsupportedProviderEndpointError
from api.domain.router import RouterRepository
from api.domain.user.views import AuthenticatedUserView
from api.utils.variables import EndpointRoute


@dataclass
class GetHealthModelsCommand:
    authenticated_user: AuthenticatedUserView


@dataclass
class GetHealthModelsUseCaseSuccess:
    models: list[ModelHealthStatus]


type GetHealthModelsUseCaseResult = GetHealthModelsUseCaseSuccess


class GetHealthModelsUseCase:
    WAITING_REQUESTS_THRESHOLD = 10
    RUNNING_REQUESTS_THRESHOLD = 100

    def __init__(
        self,
        provider_adapter_builder: ProviderAdapterBuilder,
        provider_client: ProviderClient,
        provider_metrics_logger: ProviderMetricsLogger,
        provider_repository: ProviderRepository,
        router_repository: RouterRepository,
    ):
        self.provider_adapter_builder = provider_adapter_builder
        self.provider_client = provider_client
        self.provider_metrics_logger = provider_metrics_logger
        self.provider_repository = provider_repository
        self.router_repository = router_repository

    async def execute(self, command: GetHealthModelsCommand) -> GetHealthModelsUseCaseResult:
        models = []
        routers = await self.router_repository.get_all_routers()
        providers = await self.provider_repository.get_all_providers()

        for router in routers:
            if router.has_no_providers:
                continue
            if command.authenticated_user.cannot_access_router(router_id=router.id):
                continue

            health = ModelHealthStatus(id=router.name, status=HealthStatus.GREEN)
            for provider in providers:
                if provider.router_id != router.id:
                    continue

                result = self.provider_adapter_builder.build(endpoint=EndpointRoute.METRICS, provider=provider)

                match result:
                    case ProviderAdapter() as adapter:
                        pass
                    case UnsupportedProviderEndpointError():
                        adapter = self.provider_adapter_builder.build(endpoint=EndpointRoute.MODELS, provider=provider)
                        original_request = ProviderOriginalRequest(endpoint=EndpointRoute.MODELS)
                        formatted_request = adapter.format_request(original_request=original_request)
                        response = await self.provider_client.forward_request(provider=provider, formatted_request=formatted_request)
                        match response:
                            case ProviderOriginalResponse() as response:
                                continue
                            case _:
                                health.status = HealthStatus.RED
                                continue

                original_request = ProviderOriginalRequest(endpoint=EndpointRoute.METRICS)
                formatted_request = adapter.format_request(original_request=original_request)
                response = await self.provider_client.forward_request(provider=provider, formatted_request=formatted_request)

                match response:
                    case ProviderOriginalResponse() as response:
                        pass
                    case _:
                        # @TODO: if another provider is healthy, we should not set the health to red
                        # @TODO: connect load balancing strategy to the health status
                        health.status = HealthStatus.RED
                        continue

                result = adapter.format_response(original_request=original_request, original_response=response)

                match result:
                    case ProviderFormattedResponse() as formatted_response:
                        pass
                    case ProviderAdapterValidationResponseError():
                        health.status = HealthStatus.RED
                        continue

                match provider.type:
                    case ProviderType.VLLM:
                        if health.status != HealthStatus.RED:
                            if formatted_response.data.waiting_requests > 0:
                                health.status = HealthStatus.YELLOW
                            if formatted_response.data.running_requests > 20:
                                health.status = HealthStatus.RED

                    case ProviderType.MISTRAL:
                        if health.status != HealthStatus.RED:
                            if formatted_response.data.running_requests > 58:
                                health.status = HealthStatus.YELLOW
                            if formatted_response.data.running_requests > 63:
                                health.status = HealthStatus.RED

            models.append(health)

        return GetHealthModelsUseCaseSuccess(models=models)
