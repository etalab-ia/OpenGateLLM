from abc import ABC, abstractmethod
from dataclasses import dataclass

from api.domain.model.entities import ModelType as RouterType
from api.domain.model.errors import ModelNotFoundError
from api.domain.provider.entities import Provider, ProviderType
from api.domain.provider.errors import NoAvailableProviderError, ProviderNotReachableError


@dataclass
class ProviderCapabilities:
    max_context_length: int | None
    vector_size: int | None = None


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
    ) -> ProviderCapabilities | ModelNotFoundError | ProviderNotReachableError:
        pass

    @abstractmethod
    async def get_best_provider_id(self, router_id: int, providers: list[Provider]) -> int | NoAvailableProviderError:
        pass
