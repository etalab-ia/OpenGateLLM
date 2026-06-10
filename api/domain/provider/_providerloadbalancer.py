from abc import abstractmethod

from api.domain.provider.entities import Provider
from api.domain.router.entities import RouterLoadBalancingStrategy


class ProviderLoadBalancer:
    @abstractmethod
    async def find_best_provider(self, strategy: RouterLoadBalancingStrategy, providers: list[Provider]) -> Provider:
        pass
