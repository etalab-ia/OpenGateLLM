from abc import ABC, abstractmethod

from api.domain.usage.entities import Usage


class UsageContext(ABC):
    @property
    @abstractmethod
    def request_id(self) -> str:
        pass

    @abstractmethod
    def record_router(self, router_id: int, router_name: str) -> None:
        pass

    @abstractmethod
    def record_provider(self, provider_id: int, provider_model_name: str) -> None:
        pass

    @abstractmethod
    def record_usage(self, usage: Usage) -> None:
        pass
