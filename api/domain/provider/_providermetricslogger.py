from abc import ABC, abstractmethod


class ProviderMetricsLogger(ABC):
    @abstractmethod
    async def increment_inflight(self, provider_id: int) -> bool:
        pass

    @abstractmethod
    async def decrement_inflight(self, provider_id: int) -> None:
        pass
