from abc import ABC, abstractmethod

from api.domain.provider.entities import Provider
from api.domain.router.entities import RouterLoadBalancingStrategy


class ProviderLoadBalancer(ABC):
    @abstractmethod
    async def find_best_provider(self, strategy: RouterLoadBalancingStrategy, providers: list[Provider]) -> Provider:
        pass
