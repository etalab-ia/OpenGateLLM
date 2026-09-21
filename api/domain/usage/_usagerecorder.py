from abc import ABC, abstractmethod
from datetime import datetime
from uuid import uuid4

from api.domain.usage.entities import Usage
from api.utils.variables import EndpointRoute


class UsageRecorder(ABC):
    @abstractmethod
    def start_record(
        self,
        endpoint: EndpointRoute,
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
    def update_record(self, usage: Usage, provider_id: int, provider_model_name: str, first_token_at: datetime | None = None) -> None:
        pass

    @abstractmethod
    def fail_record(self, message: str) -> None:
        pass

    @abstractmethod
    def end_record(self) -> None:
        pass


class DummyUsageRecorder(UsageRecorder):
    def start_record(
        self,
        endpoint: EndpointRoute,
        model: str,
        user_id: int,
        router_id: int,
        router_name: str,
        user_email: str,
        key_id: int,
        key_name: str,
    ) -> str:
        return uuid4().hex

    def update_record(self, usage: Usage, provider_id: int, provider_model_name: str, first_token_at: datetime | None = None) -> None:
        return

    def fail_record(self, message: str) -> None:
        return

    def end_record(self) -> None:
        return
