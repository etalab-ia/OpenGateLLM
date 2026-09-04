from ecologits.electricity_mix_repository import ElectricityMix
from ecologits.tracers.utils import compute_llm_impacts, electricity_mixes

from api.domain.model import ModelEnvironmentalImpactsComputer
from api.domain.provider.entities import HostingZone
from api.domain.usage.entities import EnvironmentalImpacts


class EcologitModelEnvironmentalImpactsComputer(ModelEnvironmentalImpactsComputer):
    def compute(
        self,
        model_active_params: int,
        model_total_params: int,
        model_zone: HostingZone,
        completion_tokens: int,
        request_latency: int,
    ) -> EnvironmentalImpacts:
        electricity_mix: ElectricityMix = electricity_mixes.find_electricity_mix(zone=model_zone.value)

        if not model_active_params or not model_total_params or not completion_tokens:
            return EnvironmentalImpacts(kWh=0.0, kgCO2eq=0.0)

        impacts = compute_llm_impacts(
            model_active_parameter_count=model_active_params,
            model_total_parameter_count=model_total_params,
            output_token_count=completion_tokens,
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

        return EnvironmentalImpacts(kWh=(impacts.energy.value or 0.0), kgCO2eq=(impacts.gwp.value or 0.0))
