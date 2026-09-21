from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

from api.domain.model.errors import StatusCodeModelError, TooBusyModelError, UnknownModelError
from api.domain.provider.entities import Provider, ProviderChunkResponse, ProviderRequest, ProviderResponse
from api.domain.provider.errors import (
    ProviderAdapterValidationRequestError,
    ProviderAdapterValidationResponseError,
    UnsupportedProviderEndpointError,
)

type ProviderClientError = (
    TooBusyModelError
    | UnknownModelError
    | StatusCodeModelError
    | ProviderAdapterValidationRequestError
    | ProviderAdapterValidationResponseError
    | UnsupportedProviderEndpointError
)
type ProviderClientResponse = ProviderResponse | ProviderClientError

type ProviderClientStreamError = ProviderAdapterValidationRequestError | UnsupportedProviderEndpointError
type ProviderClientStream = AsyncGenerator[ProviderChunkResponse] | ProviderClientStreamError


class ProviderClient(ABC):
    @abstractmethod
    async def forward(self, provider: Provider, request: ProviderRequest) -> ProviderClientResponse:
        pass

    @abstractmethod
    async def forward_stream(self, provider: Provider, request: ProviderRequest) -> ProviderClientStream:
        pass
