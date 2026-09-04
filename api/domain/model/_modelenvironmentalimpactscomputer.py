from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from api.domain.usage.entities import EnvironmentalImpacts

if TYPE_CHECKING:  # avoids a cycle: provider.entities imports model.entities
    from api.domain.provider.entities import HostingZone


class ModelEnvironmentalImpactsComputer(ABC):
    @abstractmethod
    def compute(
        self,
        model_active_params: int,
        model_total_params: int,
        model_zone: "HostingZone",
        completion_tokens: int,
        request_latency: int | None = None,
    ) -> EnvironmentalImpacts:
        """Calculate carbon impact of a model inference using direct parameters.

        Args:
            model_active_params(int): Number of active parameters (in millions or billions, must match compute_llm_impacts expectations)
            model_total_params(int): Total number of parameters (in millions or billions, must match compute_llm_impacts expectations)
            model_zone(CountryCodes): Electricity mix zone (Alpha-3 of the country code)
            completion_tokens(int): Number of output tokens
            request_latency(int | None): Latency of the inference (in milliseconds)

        Returns:
            CarbonFootprintUsage: Computed carbon footprint
        """
        pass
