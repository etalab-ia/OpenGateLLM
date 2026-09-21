from abc import ABC, abstractmethod

from api.domain.usage.entities import Usage


class UsageContext(ABC):
    @abstractmethod
    def record_router(self, router_id: int, router_name: str) -> None:
        pass

    @abstractmethod
    def record_provider(self, provider_id: int, provider_model_name: str) -> None:
        pass

    @abstractmethod
    def record_usage(self, request_id: str | None, usage: Usage) -> None:
        pass
