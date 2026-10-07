from abc import ABC, abstractmethod
from datetime import datetime

from api.domain.usage.entities import UsageBucketPage, UsageRecord


class UsageRepository(ABC):
    @abstractmethod
    def open_record(self, record: UsageRecord) -> None:
        """Called when the request arrives, before any use case runs. Postgres has nothing to do until the record is
        complete; Langfuse opens the span the provider call will be measured in."""
        pass

    @abstractmethod
    async def save_record(self, record: UsageRecord) -> None:
        """Called once the response has been sent, so `status` and `latency` are final."""
        pass

    @abstractmethod
    async def get_usage_buckets_page(
        self,
        user_id: int,
        start_time: datetime,
        end_time: datetime,
        offset: int,
        limit: int,
        endpoint: str | None = None,
        model: str | None = None,
        key_id: int | None = None,
    ) -> UsageBucketPage:
        pass
