from abc import ABC, abstractmethod
from datetime import datetime

from api.domain.usage.entities import Usage


class UsageContext(ABC):
    """What a use case may record about the request it is serving. The record itself is opened and closed by the
    HTTP layer, so a use case never has to remember to close it."""

    @abstractmethod
    def get_request_id(self) -> str:
        """The id the HTTP layer assigned to this request. The provider request and the usage record share it."""
        pass

    @abstractmethod
    def elapsed_ms(self, at: datetime | None = None) -> int:
        """Milliseconds between the moment the record was opened and `at` (now by default)."""
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
