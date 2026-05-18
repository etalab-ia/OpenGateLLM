from abc import ABC, abstractmethod

from api.domain.provider.entities import Metric


class ProviderMetricsLogger(ABC):
    @abstractmethod
    async def log_metric(self, provider_id: int, metric: Metric, value: float):
        pass

    @abstractmethod
    async def increment_inflight(self, provider_id: int) -> bool:
        pass

    @abstractmethod
    async def decrement_inflight(self, provider_id: int) -> None:
        pass

    @abstractmethod
    async def get_metric_history(self, provider_id: int, metric: Metric, from_time: int | None = None) -> list[float]:
        pass

    @abstractmethod
    async def get_current_inflight(self, provider_id: int) -> int:
        pass
