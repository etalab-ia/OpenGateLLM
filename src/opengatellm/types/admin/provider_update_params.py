# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Optional
from typing_extensions import Annotated, TypedDict

from .metric import Metric
from ..._utils import PropertyInfo
from .provider_carbon_footprint_zone import ProviderCarbonFootprintZone

__all__ = ["ProviderUpdateParams"]


class ProviderUpdateParams(TypedDict, total=False):
    model_active_params: Optional[int]
    """
    Active params of the model in billions of parameters for carbon footprint
    computation. If not provided, the total params will be used if provided, else
    carbon footprint will not be computed. For more information, see
    https://ecologits.ai
    """

    model_hosting_zone: Optional[ProviderCarbonFootprintZone]
    """
    Model hosting zone using ISO 3166-1 alpha-3 code format (e.g., `WOR` for World,
    `FRA` for France, `USA` for United States). This determines the electricity mix
    used for carbon intensity calculations. For more information, see
    https://ecologits.ai
    """

    model_total_params: Optional[int]
    """
    Total params of the model in billions of parameters for carbon footprint
    computation. If not provided, the active params will be used if provided, else
    carbon footprint will not be computed. For more information, see
    https://ecologits.ai
    """

    qos_limit: Optional[float]
    """The value to use for the quality of service.

    Depends of the metric, the value can be a percentile, a threshold, etc.
    """

    qos_metric: Optional[Metric]
    """The metric to use for the quality of service policy.

    If not provided, no QoS policy is applied.
    """

    router: Optional[int]
    """The ID of the new router to assign to the provider."""

    api_timeout: Annotated[Optional[int], PropertyInfo(alias="timeout")]
    """
    Timeout for the model provider requests, after user receive an 500 error (model
    is too busy).
    """
