from abc import ABC, abstractmethod
from datetime import datetime

from api.domain.usage.entities import Usage


class UsageContext(ABC):
    @abstractmethod
    def get_request_id(self) -> str:
        pass

    @abstractmethod
    def elapsed_ms(self, at: datetime | None = None) -> int:
        pass

    @abstractmethod
    def record_router(self, router_id: int, router_name: str) -> None:
        pass

    @abstractmethod
    def record_provider(self, provider_id: int, provider_model_name: str) -> None:
        pass

    @abstractmethod
    def record_usage(self, usage: Usage, latency: int, ttft: int | None = None) -> None:
        pass
