from abc import ABC, abstractmethod

from api.domain.provider.entities import Provider, ProviderRawResponse, ProviderRequest, ProviderResponse
from api.domain.provider.errors import ProviderAdapterValidationResponseError


class ProviderAdapter(ABC):
    provider: Provider

    @abstractmethod
    def to_domain_response(
        self,
        raw_response: ProviderRawResponse,
        request: ProviderRequest,
    ) -> ProviderResponse | ProviderAdapterValidationResponseError:
        pass
