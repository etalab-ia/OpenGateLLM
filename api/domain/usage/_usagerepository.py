from abc import ABC, abstractmethod
from datetime import datetime

from api.domain.usage.entities import UsagePage


class UsageRepository(ABC):
    @abstractmethod
    async def get_usages_page(
        self,
        user_id: int,
        start_time: datetime,
        end_time: datetime,
        offset: int,
        limit: int,
        endpoint: str | None = None,
    ) -> UsagePage:
        pass
