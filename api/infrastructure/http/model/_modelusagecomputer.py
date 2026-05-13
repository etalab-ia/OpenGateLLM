import logging

from ecologits.electricity_mix_repository import ElectricityMix
from ecologits.tracers.utils import compute_llm_impacts, electricity_mixes

from api.domain.provider.entities import HostingZone
from api.infrastructure.http.model.exchanges import ModelHttpExchange
from api.schemas.usage import EnvironmentalImpacts, Usage

from ._modeltokenizercomputer import ModelTokenizerComputer

logger = logging.getLogger(__name__)


class ModelUsageComputer:
    def __init__(
        self,
        tokenizer_computer: ModelTokenizerComputer,
        model_hosting_zone: HostingZone,
        model_total_params: int | None,
        model_active_params: int | None,
    ):
        self.tokenizer_computer = tokenizer_computer
        self.model_hosting_zone = model_hosting_zone
        self.model_total_params = model_total_params
        self.model_active_params = model_active_params

    def compute(
        self,
        exchange: ModelHttpExchange,
        usage: Usage,
        cost_prompt_tokens: float | None,
        cost_completion_tokens: float | None,
    ) -> Usage:
        updated_usage = usage.model_copy(deep=True)
        try:
            prompt_tokens = self.tokenizer_computer.compute_prompt_tokens(
                endpoint=exchange.original_request.endpoint,
                body=exchange.original_request.body,
            )

            completion_tokens = self.tokenizer_computer.compute_completion_tokens(
                endpoint=exchange.original_request.endpoint,
                response_data=exchange.original_response.data,
            )

            total_tokens = prompt_tokens + completion_tokens

            carbon_footprint = self._get_carbon_footprint(
                active_params=self.model_active_params,
                total_params=self.model_total_params,
                model_zone=self.model_hosting_zone,
                token_count=total_tokens,
                request_latency=exchange.original_response.latency,
            )
            cost = round(prompt_tokens / 1000000 * cost_prompt_tokens + completion_tokens / 1000000 * cost_completion_tokens, ndigits=6)  # fmt: off

            updated_usage = usage.model_copy(
                update={
                    "prompt_tokens": usage.prompt_tokens + prompt_tokens,
                    "completion_tokens": usage.completion_tokens + completion_tokens,
                    "total_tokens": usage.total_tokens + total_tokens,
                    "cost": usage.cost + cost,
                    "carbon": usage.carbon.model_copy(
                        update={
                            "kgCO2eq": usage.carbon.kgCO2eq + carbon_footprint.kgCO2eq,
                            "kWh": usage.carbon.kWh + carbon_footprint.kWh,
                        }
                    ),
                    "requests": usage.requests + 1,
                }
            )

        except Exception as e:
            # @TODO: handle error
            logger.exception(msg=f"Failed to compute usage values for endpoint {exchange.original_request.endpoint}: {e}.")

        return updated_usage

    @staticmethod
    def _get_carbon_footprint(
        active_params: int,
        total_params: int,
        model_zone: HostingZone,
        token_count: int,
        request_latency: int | None = None,
    ) -> EnvironmentalImpacts:
        """Calculate carbon impact of a model inference using direct parameters.

        Args:
            active_params(int): Number of active parameters (in millions or billions, must match compute_llm_impacts expectations)
            total_params(int): Total number of parameters (in millions or billions, must match compute_llm_impacts expectations)
            model_zone(CountryCodes): Electricity mix zone (Alpha-3 of the country code)
            token_count(int): Number of output tokens
            request_latency(int | None): Latency of the inference (in milliseconds)

        Returns:
            CarbonFootprintUsage: Computed carbon footprint
        """
        electricity_mix: ElectricityMix = electricity_mixes.find_electricity_mix(zone=model_zone.value)

        if not active_params or not total_params:
            return EnvironmentalImpacts(kWh=0, kgCO2eq=0)

        impacts = compute_llm_impacts(
            model_active_parameter_count=active_params,
            model_total_parameter_count=total_params,
            output_token_count=token_count,
            if_electricity_mix_adpe=electricity_mix.adpe,  # Abiotic Depletion Potential
            if_electricity_mix_pe=electricity_mix.pe,  # Primary Energy
            if_electricity_mix_gwp=electricity_mix.gwp,  # Global Warming Potential (CO2)
            if_electricity_mix_wue=electricity_mix.wue,
            # Datacenter efficiency parameters (industry average values)
            # PUE: Power Usage Effectiveness (1.0 = perfect, typical hyperscaler ~1.2)
            # WUE: Water Usage Effectiveness (L/kWh, typical ~1.8)
            datacenter_pue=1.2,
            datacenter_wue=1.8,
            request_latency=request_latency / 1000,  # convert to seconds
        )
        impacts = EnvironmentalImpacts(kWh=impacts.energy.value, kgCO2eq=impacts.gwp.value)

        return impacts
