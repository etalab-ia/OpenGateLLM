from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from api.domain.model.errors import StatusCodeModelError, TooBusyModelError, UnknownModelError
from api.domain.provider.entities import Provider, ProviderFormattedRequest, ProviderOriginalResponse

type ProviderClientResponse = ProviderOriginalResponse | TooBusyModelError | UnknownModelError | StatusCodeModelError


class ProviderClient(ABC):
    @abstractmethod
    async def forward_request(self, provider: Provider, formatted_request: ProviderFormattedRequest) -> ProviderClientResponse:
        pass

    @abstractmethod
    async def forward_stream(self, provider: Provider, formatted_request: ProviderFormattedRequest) -> AsyncGenerator[Any]:
        pass
