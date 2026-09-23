from abc import ABC, abstractmethod
from datetime import datetime

from api.domain.provider.entities import ProviderEndpoint
from api.domain.usage.entities import Usage


class UsageRecorder(ABC):
    @abstractmethod
    def start_record(
        self,
        endpoint: ProviderEndpoint,
        model: str,
        user_id: int,
        router_id: int,
        router_name: str,
        user_email: str,
        key_id: int,
        key_name: str,
    ) -> str:
        """Start a record and return the request id."""
        pass

    @abstractmethod
    def compute_elapsed_ms(self, end_time: datetime | None = None) -> int:
        pass

    @abstractmethod
    def update_record(self, usage: Usage, provider_id: int, provider_model_name: str, first_token_at: datetime | None = None) -> None:
        pass

    @abstractmethod
    def fail_record(self, message: str, status_code: int) -> None:
        pass

    @abstractmethod
    def end_record(self) -> None:
        pass
