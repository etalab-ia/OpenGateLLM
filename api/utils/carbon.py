import logging

from ecologits.tracers.utils import compute_llm_impacts, electricity_mixes

from api.schemas.admin.providers import ProviderCarbonFootprintZone
from api.schemas.usage import CarbonFootprintUsage, CarbonFootprintUsageKgCO2eq, CarbonFootprintUsageKWh

logger = logging.getLogger(__name__)


def get_carbon_footprint(
    active_params: int,
    total_params: int | None,
    model_zone: ProviderCarbonFootprintZone,
    token_count: int,
    request_latency: float,
) -> CarbonFootprintUsage:
    """Calculate carbon impact of a model inference using direct parameters.

    Args:
        active_params(int): Number of active parameters (in millions or billions, must match compute_llm_impacts expectations)
        total_params(int): Total number of parameters (in millions or billions, must match compute_llm_impacts expectations)
        model_zone(CountryCodes): Electricity mix zone (Alpha-3 of the country code)
        token_count(int): Number of output tokens
        request_latency(float): Latency of the inference (in milliseconds)

    Returns:
        CarbonFootprintUsage: Computed carbon footprint
    """
    assert request_latency >= 0, "request_latency must be a positive number"

    # Short-circuit when we cannot (or should not) compute impacts.
    # This avoids calling ecologits with missing model parameters and matches unit-test expectations.
    if token_count <= 0 or active_params <= 0 or total_params in (None, 0):
        return CarbonFootprintUsage(
            kWh=CarbonFootprintUsageKWh(min=0.0, max=0.0),
            kgCO2eq=CarbonFootprintUsageKgCO2eq(min=0.0, max=0.0),
        )

    electricity_mix = electricity_mixes.find_electricity_mix(zone=model_zone.value)
    if not electricity_mix:
        raise ValueError(f"Electricity zone {model_zone.value} not found")

    impacts = compute_llm_impacts(
        model_active_parameter_count=active_params,
        model_total_parameter_count=total_params,
        output_token_count=token_count,
        if_electricity_mix_adpe=electricity_mix.adpe,
        if_electricity_mix_pe=electricity_mix.pe,
        if_electricity_mix_gwp=electricity_mix.gwp,
        request_latency=request_latency / 1000,  # convert to seconds
    )
    carbon_footprint = CarbonFootprintUsage(
        kWh=CarbonFootprintUsageKWh(min=impacts.energy.value.min, max=impacts.energy.value.max),
        kgCO2eq=CarbonFootprintUsageKgCO2eq(min=impacts.gwp.value.min, max=impacts.gwp.value.max),
    )

    return carbon_footprint
