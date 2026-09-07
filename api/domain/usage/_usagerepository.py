from abc import ABC, abstractmethod
from datetime import datetime

from api.domain.usage.entities import UsageBucketPage


class UsageRepository(ABC):
    @abstractmethod
    async def get_usage_buckets_page(
        self,
        user_id: int,
        start_time: datetime,
        end_time: datetime,
        offset: int,
        limit: int,
        endpoint: str | None = None,
        models: list[str] | None = None,
        key_id: int | None = None,
    ) -> UsageBucketPage:
        pass
