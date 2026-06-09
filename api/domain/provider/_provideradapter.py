from abc import ABC, abstractmethod

from api.domain.provider.entities import (
    Provider,
    ProviderFormattedRequest,
    ProviderFormattedResponse,
    ProviderOriginalRequest,
    ProviderOriginalResponse,
)
from api.domain.provider.errors import ProviderAdapterValidationRequestError, ProviderAdapterValidationResponseError


class ProviderAdapter(ABC):
    provider: Provider

    @abstractmethod
    def format_request(self, original_request: ProviderOriginalRequest) -> ProviderFormattedRequest | ProviderAdapterValidationRequestError:
        pass

    @abstractmethod
    def format_response(
        self,
        original_response: ProviderOriginalResponse,
        original_request: ProviderOriginalRequest,
    ) -> ProviderFormattedResponse | ProviderAdapterValidationResponseError:
        pass
