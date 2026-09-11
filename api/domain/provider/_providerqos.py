from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
import math
import random

from api.domain.provider.entities import Provider
from api.domain.router.entities import RouterLoadBalancingStrategy


@dataclass
class ProviderAdmissionFull:
    depth: int

    def retry_after(self, retries: int | None) -> int:
        retry_after_ceiling = 1 if retries is None else max(1, math.ceil(retries * 0.5))
        jitter = math.ceil((1 + self.depth) * (0.5 + random.random()))
        return max(1, min(retry_after_ceiling, jitter))


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
