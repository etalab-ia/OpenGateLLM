from dataclasses import dataclass

from api.domain.model.entities import HealthStatus, ModelHealthStatus
from api.domain.provider import ProviderClient, ProviderQoS, ProviderRepository
from api.domain.provider.entities import ProviderRequest, ProviderResponse
from api.domain.provider.errors import ProviderAdapterValidationResponseError
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
    LIVENESS_TIMEOUT_SECONDS = 4
    ORANGE_LOAD_RATIO = 0.95
    STATUS_PRIORITY = {
        HealthStatus.RED: 0,
        HealthStatus.ORANGE: 1,
        HealthStatus.GREEN: 2,
    }

    def __init__(
        self,
        provider_client: ProviderClient,
        provider_qos: ProviderQoS,
        provider_repository: ProviderRepository,
        router_repository: RouterRepository,
    ):
        self.provider_client = provider_client
        self.provider_qos = provider_qos
        self.provider_repository = provider_repository
        self.router_repository = router_repository

    @classmethod
    def _provider_status(cls, liveness_ok: bool, load: int, qos_limit: int | None) -> HealthStatus:
        if not liveness_ok or qos_limit == 0 or (qos_limit is not None and load >= qos_limit):
            return HealthStatus.RED
        if qos_limit is not None and load >= cls.ORANGE_LOAD_RATIO * qos_limit:
            return HealthStatus.ORANGE
        return HealthStatus.GREEN

    async def execute(self, command: GetHealthModelsCommand) -> GetHealthModelsUseCaseResult:
        models = []
        routers = await self.router_repository.get_all_routers()
        providers = await self.provider_repository.get_all_providers()
        loads = await self.provider_qos.get_loads(provider_ids=[provider.id for provider in providers])

        for router in routers:
            if router.has_no_providers:
                continue
            if command.authenticated_user.cannot_access_router(router_id=router.id):
                continue

            provider_statuses = []
            for provider in (provider for provider in providers if provider.router_id == router.id):
                response = await self.provider_client.forward(
                    provider=provider.with_timeout(self.LIVENESS_TIMEOUT_SECONDS),
                    request=ProviderRequest(endpoint=EndpointRoute.MODELS),
                )
                liveness_ok = isinstance(response, ProviderResponse | ProviderAdapterValidationResponseError)
                provider_statuses.append(
                    self._provider_status(
                        liveness_ok=liveness_ok,
                        load=loads[provider.id],
                        qos_limit=provider.qos_limit,
                    )
                )

            if provider_statuses:
                models.append(
                    ModelHealthStatus(
                        id=router.name,
                        status=max(provider_statuses, key=self.STATUS_PRIORITY.__getitem__),
                    )
                )

        return GetHealthModelsUseCaseSuccess(models=models)
