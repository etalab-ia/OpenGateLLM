from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass

from api.domain.provider.entities import Provider
from api.domain.router.entities import RouterLoadBalancingStrategy


@dataclass
class ProviderAdmissionFull:
    depth: int


type ProviderAdmissionResult = Provider | ProviderAdmissionFull


class ProviderQoS(ABC):
    @abstractmethod
    def admit(
        self,
        request_id: str,
        providers: list[Provider],
        strategy: RouterLoadBalancingStrategy,
        enforce_limit: bool,
    ) -> AbstractAsyncContextManager[ProviderAdmissionResult]:
        pass

    @abstractmethod
    async def get_loads(self, provider_ids: list[int]) -> dict[int, int]:
        pass
