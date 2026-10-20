from abc import ABC, abstractmethod
from datetime import datetime

from api.domain.usage.entities import UsageBucketPage, UsageRecord


class UsageRepository(ABC):
    @abstractmethod
    def save_record(self, record: UsageRecord) -> None:
        """Schedules the write and returns at once: a stream the client abandoned calls it from a cancelled task, where
        any await would raise before the row is written."""
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
