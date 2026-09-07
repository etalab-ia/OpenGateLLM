from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from api.domain.model.errors import StatusCodeModelError, TooBusyModelError, UnknownModelError
from api.domain.provider.entities import Provider, ProviderRequest, ProviderResponse
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


class ProviderClient(ABC):
    @abstractmethod
    async def forward(self, provider: Provider, request: ProviderRequest) -> ProviderClientResponse:
        pass

    @abstractmethod
    async def forward_stream(self, provider: Provider, request: ProviderRequest) -> AsyncGenerator[Any]:
        pass
