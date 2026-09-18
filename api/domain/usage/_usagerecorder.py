from abc import ABC, abstractmethod
from datetime import datetime
from uuid import uuid4

from api.domain.usage.entities import Usage


class UsageRecorder(ABC):
    @abstractmethod
    def start_record(self, name: str, model: str, user_id: int) -> str:
        """Start a record and return the request id."""
        pass

    @abstractmethod
    def update_record(self, usage: Usage, provider_id: int, first_token_at: datetime | None = None) -> None:
        pass

    @abstractmethod
    def fail_record(self, message: str) -> None:
        pass

    @abstractmethod
    def end_record(self) -> None:
        pass


class DummyUsageRecorder(UsageRecorder):
    def start_record(self, name: str, model: str, user_id: int) -> str:
        return uuid4().hex

    def update_record(self, usage: Usage, provider_id: int, first_token_at: datetime | None = None) -> None:
        return

    def fail_record(self, message: str) -> None:
        return

    def end_record(self) -> None:
        return
