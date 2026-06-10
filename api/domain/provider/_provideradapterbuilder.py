from abc import ABC, abstractmethod

from api.domain.provider._provideradapter import ProviderAdapter
from api.domain.provider.entities import Provider
from api.domain.provider.errors import UnsupportedProviderEndpointError
from api.utils.variables import EndpointRoute


class ProviderAdapterBuilder(ABC):
    @abstractmethod
    def build(self, endpoint: EndpointRoute, provider: Provider) -> ProviderAdapter | UnsupportedProviderEndpointError:
        pass
