from dataclasses import dataclass
import statistics
import time

from api.domain.model.entities import HealthStatus, ModelHealthStatus
from api.domain.provider import ProviderMetricsLogger, ProviderRepository
from api.domain.router import RouterRepository
from api.domain.user import UserWithRoleQuery
from api.domain.user.errors import UserExpiredError
from api.utils.variables import METRICS__TIMESERIE_RETENTION_SECONDS


@dataclass
class GetHealthModelsCommand:
    user_id: str


@dataclass
class GetHealthModelsUseCaseSuccess:
    models: list[ModelHealthStatus]


type GetHealthModelsUseCaseResult = GetHealthModelsUseCaseSuccess | UserExpiredError


class GetHealthModelsUseCase:
    def __init__(
        self,
        provider_metrics_logger: ProviderMetricsLogger,
        router_repository: RouterRepository,
        provider_repository: ProviderRepository,
        user_with_role_query: UserWithRoleQuery,
    ):
        self.provider_metrics_logger = provider_metrics_logger
        self.router_repository = router_repository
        self.provider_repository = provider_repository
        self.provider_metrics_logger = provider_metrics_logger
        self.user_with_role_query = user_with_role_query

    async def execute(self, command: GetHealthModelsCommand) -> GetHealthModelsUseCaseResult:
        user = await self.user_with_role_query.get_user_with_role_by_id(user_id=command.user_id)

        if user.expires is not None and user.expires < time.time():
            return UserExpiredError()

        models = []
        routers = await self.router_repository.get_all_routers()
        providers = await self.provider_repository.get_all_providers()
        for router in routers:
            if not router.has_providers:
                continue
            if not user.has_access_to_router(router_id=router.id):
                continue

            status = ModelHealthStatus(id=router.name, status=HealthStatus.GREEN)
            for provider in providers:
                if provider.router_id != router.id:
                    continue

                historical_latencies_ms = await self.provider_metrics_logger.get_historical_normalized_latencies(provider_id=provider.id)
                if len(historical_latencies_ms) == 0:
                    continue
                current_inflight = await self.provider_metrics_logger.get_current_inflight(provider_id=provider.id)

                request_per_ms = len(historical_latencies_ms) / (METRICS__TIMESERIE_RETENTION_SECONDS * 1000)

                mean_latency_ms = statistics.median(data=historical_latencies_ms)
                expected_inflight = mean_latency_ms * request_per_ms

                health_indicator = current_inflight / max(expected_inflight, 0.1)  # Little's law indicator

                if health_indicator >= 1.1:
                    status.status = HealthStatus.RED
                elif health_indicator >= 0.8 and status.status != HealthStatus.RED:
                    status.status = HealthStatus.YELLOW

            models.append(status)

        return GetHealthModelsUseCaseSuccess(models=models)
