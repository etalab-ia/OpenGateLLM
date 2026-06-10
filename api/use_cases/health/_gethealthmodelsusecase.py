from dataclasses import dataclass
import time

from api.domain.model.entities import HealthStatus, ModelHealthStatus
from api.domain.provider import ProviderMetricsLogger, ProviderRepository
from api.domain.provider.entities import Metric
from api.domain.router import RouterRepository
from api.domain.user import UserWithRoleQuery
from api.domain.user.errors import UserExpiredError

# Health is based on the 95th percentile of provider throughput
# (derived from normalized latency per token) over the last HEALTH_WINDOW_SECONDS.
#
# RED    if p95 throughput < 20 tok/s
# YELLOW if p95 throughput < 60 tok/s
# GREEN  otherwise

HEALTH_WINDOW_SECONDS = 5 * 60
RED_THROUGHPUT_TOK_PER_SEC = 20
YELLOW_THROUGHPUT_TOK_PER_SEC = 60


@dataclass
class GetHealthModelsCommand:
    user_id: int


@dataclass
class GetHealthModelsUseCaseSuccess:
    models: list[ModelHealthStatus]


type GetHealthModelsUseCaseResult = GetHealthModelsUseCaseSuccess | UserExpiredError


class GetHealthModelsUseCase:
    def __init__(
        self,
        provider_metrics_logger: ProviderMetricsLogger,
        provider_repository: ProviderRepository,
        router_repository: RouterRepository,
        user_with_role_query: UserWithRoleQuery,
    ):
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
        from_time_ms = int(time.time() * 1000) - HEALTH_WINDOW_SECONDS * 1000

        for router in routers:
            if router.has_no_providers:
                continue
            if user.cannot_access_router(router_id=router.id):
                continue

            health = ModelHealthStatus(id=router.name, status=HealthStatus.GREEN)
            for provider in providers:
                if provider.router_id != router.id:
                    continue

                historical_normalized_latencies_ms = await self.provider_metrics_logger.get_metric_history(
                    provider_id=provider.id,
                    metric=Metric.NORMALIZED_LATENCY,
                    from_time=from_time_ms,
                )
                throughputs_tok_per_sec = [1000.0 / x for x in historical_normalized_latencies_ms if x > 0]
                if not throughputs_tok_per_sec:
                    continue

                sorted_throughputs = sorted(throughputs_tok_per_sec)
                p95_throughput_tok_per_sec = sorted_throughputs[int(0.95 * len(sorted_throughputs))]

                if p95_throughput_tok_per_sec < RED_THROUGHPUT_TOK_PER_SEC:
                    health.status = HealthStatus.RED
                elif p95_throughput_tok_per_sec < YELLOW_THROUGHPUT_TOK_PER_SEC and health.status != HealthStatus.RED:
                    health.status = HealthStatus.YELLOW

            models.append(health)

        return GetHealthModelsUseCaseSuccess(models=models)
