from abc import ABC, abstractmethod

from api.domain.model.entities import Metric
from api.domain.provider.entities import Provider, ProviderCarbonFootprintZone, ProviderType
from api.domain.provider.errors import ProviderAlreadyExistsError


class ProviderRepository(ABC):
    @abstractmethod
    async def create_provider(
        self,
        router_id: int,
        user_id: int,
        provider_type: ProviderType,
        url: str,
        key: str | None,
        timeout: int,
        model_name: str,
        model_hosting_zone: ProviderCarbonFootprintZone,
        model_total_params: int,
        model_active_params: int,
        qos_metric: Metric | None,
        qos_limit: float | None,
        vector_size: int,
        max_context_length: int,
    ) -> Provider | ProviderAlreadyExistsError:
        pass
