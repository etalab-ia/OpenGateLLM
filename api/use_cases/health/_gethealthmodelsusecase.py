from dataclasses import dataclass
import time

from api.domain.provider import ProviderMetricsLogger, ProviderRepository
from api.domain.router import RouterRepository
from api.domain.user import UserWithRoleQuery
from api.domain.user.errors import UserExpiredError


@dataclass
class GetHealthModelsCommand:
    user_id: str


@dataclass
class GetHealthModelsUseCaseSuccess:
    pass


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
        self.provider_metrics_logger = router_repository
        self.user_with_role_query = user_with_role_query

    async def execute(self, command: GetHealthModelsCommand) -> GetHealthModelsUseCaseResult:
        user = await self.user_with_role_query.get_user_with_role_by_id(user_id=command.user_id)

        if user.expires is not None and user.expires < time.time():
            return UserExpiredError()

        routers = await self.router_repository.get_all_routers()

        selected_routers = []
        for router in routers:
            if router.has_providers:
                if user.has_access_to_router(router_id=router.id):
                    selected_routers.append([router])

        providers = await self.provider_repository.get_all_providers()
        for router in selected_routers:
            router.provider = []
            for provider in providers:
                if provider.router_id == router.id:
                    router.provider.append(provider)

        # get the list of routers and providers
        # get the metric values for each provider
        # take the best value
        # determine the model state
        # return the state
