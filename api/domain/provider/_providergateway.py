from abc import ABC, abstractmethod
from dataclasses import dataclass

from api.domain.model import ModelType as RouterType
from api.domain.provider.entities import ProviderType
from api.domain.provider.errors import ProviderNotReachableError


@dataclass
class ProviderCapabilities:
    max_context_length: int | None
    vector_size: int | None


class ProviderGateway(ABC):
    @abstractmethod
    async def get_capabilities(
        self,
        router_type: RouterType,
        provider_type: ProviderType,
        url: str,
        key: str | None,
        timeout: int,
        model_name: str,
    ) -> ProviderCapabilities | ProviderNotReachableError:
        pass
