from ecologits.tracers.utils import compute_llm_impacts, electricity_mixes

from api.schemas.admin.providers import ProviderCarbonFootprintZone
from api.schemas.usage import CarbonFootprintUsage


def get_carbon_footprint(
    active_params: int,
    total_params: int,
    model_zone: ProviderCarbonFootprintZone,
    token_count: int,
    request_latency: int | None = None,
) -> CarbonFootprintUsage:
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
    electricity_mix = electricity_mixes.find_electricity_mix(zone=model_zone.value)
    if not electricity_mix:
        raise ValueError(f"Electricity zone {model_zone.value} not found")

    if not active_params or not total_params:
        return CarbonFootprintUsage(kWh=0, kgCO2eq=0)

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
    carbon_footprint = CarbonFootprintUsage(kWh=impacts.energy.value, kgCO2eq=impacts.gwp.value)

    return carbon_footprint
