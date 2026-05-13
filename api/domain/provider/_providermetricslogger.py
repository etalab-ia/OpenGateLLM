from abc import ABC, abstractmethod


class ProviderMetricsLogger(ABC):
    @abstractmethod
    async def log_performance(self, provider_id: int | None, ttft: int | None, latency: int | None) -> None:
        pass

    @abstractmethod
    async def increment_inflight(self, provider_id: int | None) -> bool:
        pass

    @abstractmethod
    async def decrement_inflight(self, provider_id: int | None, inflight_is_incremented: bool) -> None:
        pass

    @abstractmethod
    async def get_historical_normalized_latencies(self, provider_id: int, from_time: int | None = None) -> list[float]:
        pass

    @abstractmethod
    async def get_current_inflight(self, provider_id: int) -> int:
        pass
