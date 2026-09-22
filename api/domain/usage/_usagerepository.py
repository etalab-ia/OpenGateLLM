from abc import ABC, abstractmethod
from datetime import datetime

from api.domain.usage.entities import Usage, UsageBucketPage
from api.utils.variables import EndpointRoute


class UsageRepository(ABC):
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
