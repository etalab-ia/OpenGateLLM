from dataclasses import dataclass

from api.domain.model.entities import HealthStatus, ModelHealthStatus
from api.domain.provider import ProviderClient, ProviderMetricsLogger, ProviderRepository
from api.domain.provider.entities import ProviderRequest, ProviderResponse, ProviderType
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
        provider_client: ProviderClient,
        provider_metrics_logger: ProviderMetricsLogger,
        provider_repository: ProviderRepository,
        router_repository: RouterRepository,
    ):
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

                request = ProviderRequest(endpoint=EndpointRoute.METRICS)
                response = await self.provider_client.forward(provider=provider, request=request)

                match response:
                    case ProviderResponse() as provider_response:
                        pass
                    case UnsupportedProviderEndpointError():
                        request = ProviderRequest(endpoint=EndpointRoute.MODELS)
                        response = await self.provider_client.forward(provider=provider, request=request)
                        match response:
                            # the fallback only probes liveness: an unparsable payload still proves the provider answered
                            case ProviderResponse() | ProviderAdapterValidationResponseError():
                                continue
                            case _:
                                health.status = HealthStatus.RED
                                continue
                    case _:
                        # @TODO: if another provider is healthy, we should not set the health to red
                        # @TODO: connect load balancing strategy to the health status
                        health.status = HealthStatus.RED
                        continue

                match provider.type:
                    case ProviderType.VLLM:
                        if health.status != HealthStatus.RED:
                            if provider_response.data.waiting_requests > 0:
                                health.status = HealthStatus.YELLOW
                            if provider_response.data.running_requests > 20:
                                health.status = HealthStatus.RED

                    case ProviderType.MISTRAL:
                        if health.status != HealthStatus.RED:
                            if provider_response.data.running_requests > 58:
                                health.status = HealthStatus.YELLOW
                            if provider_response.data.running_requests > 63:
                                health.status = HealthStatus.RED

            models.append(health)

        return GetHealthModelsUseCaseSuccess(models=models)
