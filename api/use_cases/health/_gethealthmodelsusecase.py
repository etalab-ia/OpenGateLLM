from dataclasses import dataclass

from api.domain.model.entities import HealthStatus, ModelHealthStatus
from api.domain.provider import ProviderConcurrencyLimiter, ProviderLimitsCannotBeEnforced, ProviderRepository
from api.domain.provider.entities import Provider, ProviderLoads
from api.domain.router import RouterRepository
from api.domain.router.entities import Router
from api.domain.user.views import AuthenticatedUserView

from ._providerlivenessprobe import ProviderLivenessProbe


@dataclass
class GetHealthModelsCommand:
    authenticated_user: AuthenticatedUserView


@dataclass
class GetHealthModelsUseCaseSuccess:
    models: list[ModelHealthStatus]


type GetHealthModelsUseCaseResult = GetHealthModelsUseCaseSuccess


class GetHealthModelsUseCase:
    def __init__(
        self,
        provider_liveness_probe: ProviderLivenessProbe,
        provider_concurrency_limiter: ProviderConcurrencyLimiter,
        provider_repository: ProviderRepository,
        router_repository: RouterRepository,
    ):
        self.provider_liveness_probe = provider_liveness_probe
        self.provider_concurrency_limiter = provider_concurrency_limiter
        self.provider_repository = provider_repository
        self.router_repository = router_repository

    async def execute(self, command: GetHealthModelsCommand) -> GetHealthModelsUseCaseResult:
        routers = await self.router_repository.get_all_routers()
        providers = await self.provider_repository.get_all_providers()

        match await self.provider_concurrency_limiter.read_loads(providers=providers):
            case ProviderLoads() as loads:
                pass
            case ProviderLimitsCannotBeEnforced():
                loads = None

        routers_to_check = [
            router for router in routers if router.has_providers and command.authenticated_user.can_access_router(router_id=router.id)
        ]
        models = [await self._get_model_health(router, providers, loads) for router in routers_to_check]

        return GetHealthModelsUseCaseSuccess(models=models)

    async def _get_model_health(self, router: Router, providers: list[Provider], loads: ProviderLoads | None) -> ModelHealthStatus:
        providers_of_router = [provider for provider in providers if provider.router_id == router.id]
        provider_statuses = []
        for provider in providers_of_router:
            is_live = await self.provider_liveness_probe.is_live(provider=provider)
            load = loads.load_of(provider) if loads is not None else None
            provider_status = HealthStatus.of_provider(provider=provider, is_live=is_live, load=load)
            provider_statuses.append(provider_status)

        return ModelHealthStatus(id=router.name, status=HealthStatus.best_of(provider_statuses))
