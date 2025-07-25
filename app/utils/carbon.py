import logging
from typing import Optional

from ecologits.tracers.utils import compute_llm_impacts, electricity_mixes

from app.schemas.core.configuration import CountryCodes
from app.schemas.usage import CarbonFootprintUsage, CarbonFootprintUsageKgCO2eq, CarbonFootprintUsageKWh

logger = logging.getLogger(__name__)


def get_carbon_footprint(
    active_params: Optional[int],
    total_params: Optional[int],
    model_zone: CountryCodes,
    token_count: int,
    request_latency: float,
) -> CarbonFootprintUsage:
    """Calculate carbon impact of a model inference using direct parameters.

    Args:
        active_params(Optional[int]): Number of active parameters (in millions or billions, must match compute_llm_impacts expectations)
        total_params(Optional[int]): Total number of parameters (in millions or billions, must match compute_llm_impacts expectations)
        model_zone(CountryCodes): Electricity mix zone (Alpha-3 of the country code)
        token_count(int): Number of output tokens
        request_latency(float): Latency of the inference (in seconds)

    Returns:
        CarbonFootprintUsage: Computed carbon footprint
    """
    if total_params is None or token_count == 0:
        return CarbonFootprintUsage(
            kWh=CarbonFootprintUsageKWh(min=0, max=0),
            kgCO2eq=CarbonFootprintUsageKgCO2eq(min=0, max=0),
        )

    if not isinstance(token_count, (int, float)) or token_count < 0:
        raise ValueError("token_count must be a positive number")
    if not isinstance(request_latency, (int, float)) or request_latency < 0:
        raise ValueError("request_latency must be a positive number")

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
        request_latency=request_latency,
    )
    carbon_footprint = CarbonFootprintUsage(
        kWh=CarbonFootprintUsageKWh(min=impacts.energy.value.min, max=impacts.energy.value.max),
        kgCO2eq=CarbonFootprintUsageKgCO2eq(min=impacts.gwp.value.min, max=impacts.gwp.value.max),
    )

    return carbon_footprint
