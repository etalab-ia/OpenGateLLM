from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from api.domain.model.errors import StatusCodeModelError, TooBusyModelError, UnknownModelError
from api.domain.provider.entities import Provider, ProviderRawResponse, ProviderRequest
from api.domain.provider.errors import ProviderAdapterValidationRequestError, UnsupportedProviderEndpointError

type ProviderClientResponse = (
    ProviderRawResponse
    | TooBusyModelError
    | UnknownModelError
    | StatusCodeModelError
    | ProviderAdapterValidationRequestError
    | UnsupportedProviderEndpointError
)


class ProviderClient(ABC):
    @abstractmethod
    async def forward(self, provider: Provider, request: ProviderRequest) -> ProviderClientResponse:
        pass

    @abstractmethod
    async def forward_stream(self, provider: Provider, request: ProviderRequest) -> AsyncGenerator[Any]:
        pass
