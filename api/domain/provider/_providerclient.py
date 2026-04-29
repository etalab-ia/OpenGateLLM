from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from api.domain.provider.entities import Provider, ProviderFormattedRequest, ProviderOriginalResponse


class ProviderClient(ABC):
    @abstractmethod
    def log_metrics(func):
        pass

    @log_metrics
    @abstractmethod
    async def forward_request(self, provider: Provider, formatted_request: ProviderFormattedRequest) -> ProviderOriginalResponse:
        pass

    @log_metrics
    @abstractmethod
    async def forward_stream(self, provider: Provider, formatted_request: ProviderFormattedRequest) -> AsyncGenerator[Any]:
        pass
