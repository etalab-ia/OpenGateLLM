from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from api.domain.provider.entities import Provider
from api.utils.variables import EndpointRoute

if TYPE_CHECKING:
    from api.infrastructure.http.adapters._baseadapter import BaseAdapter


class ProviderAdapterBuilder(ABC):
    @abstractmethod
    def build(self, provider: Provider, endpoint: EndpointRoute, cost_completion_tokens: float, cost_prompt_tokens: float) -> "BaseAdapter":
        pass
