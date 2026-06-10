from dataclasses import dataclass

from api.domain.model.entities import HealthStatus, ModelHealthStatus
from api.domain.provider import ProviderAdapter, ProviderAdapterBuilder, ProviderClient, ProviderMetricsLogger, ProviderRepository
from api.domain.provider.entities import ProviderFormattedResponse, ProviderOriginalRequest, ProviderOriginalResponse
from api.domain.provider.errors import ProviderAdapterValidationResponseError, UnsupportedProviderEndpointError
from api.domain.router import RouterRepository
from api.domain.user import UserWithRoleQuery
from api.domain.user.errors import UserExpiredError
from api.utils.variables import EndpointRoute


@dataclass
class GetHealthModelsCommand:
    user_id: int


@dataclass
class GetHealthModelsUseCaseSuccess:
    models: list[ModelHealthStatus]


type GetHealthModelsUseCaseResult = GetHealthModelsUseCaseSuccess | UserExpiredError


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
        user_with_role_query: UserWithRoleQuery,
    ):
        self.provider_adapter_builder = provider_adapter_builder
        self.provider_client = provider_client
        self.provider_metrics_logger = provider_metrics_logger
        self.provider_repository = provider_repository
        self.router_repository = router_repository
        self.user_with_role_query = user_with_role_query

    async def execute(self, command: GetHealthModelsCommand) -> GetHealthModelsUseCaseResult:
        user = await self.user_with_role_query.get_user_with_role_by_id(user_id=command.user_id)

        if user.has_expired:
            return UserExpiredError()

        models = []
        routers = await self.router_repository.get_all_routers()
        providers = await self.provider_repository.get_all_providers()

        for router in routers:
            if router.has_no_providers:
                continue
            if user.cannot_access_router(router_id=router.id):
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
                        print(response)
                        health.status = HealthStatus.RED
                        continue

                result = adapter.format_response(original_request=original_request, original_response=response)
                print(f"formatted response: {result}")
                match result:
                    case ProviderFormattedResponse() as formatted_response:
                        pass
                    case ProviderAdapterValidationResponseError():
                        health.status = HealthStatus.RED
                        continue

                if formatted_response.data.waiting_requests > self.WAITING_REQUESTS_THRESHOLD and health.status != HealthStatus.RED:
                    health.status = HealthStatus.YELLOW
                elif formatted_response.data.running_requests > self.RUNNING_REQUESTS_THRESHOLD and health.status != HealthStatus.RED:
                    health.status = HealthStatus.YELLOW

            models.append(health)

        return GetHealthModelsUseCaseSuccess(models=models)
