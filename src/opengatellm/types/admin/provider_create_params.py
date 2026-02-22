# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Optional
from typing_extensions import Required, Annotated, TypedDict

from .metric import Metric
from ..._utils import PropertyInfo
from .provider_type import ProviderType
from .provider_carbon_footprint_zone import ProviderCarbonFootprintZone

__all__ = ["ProviderCreateParams"]


class ProviderCreateParams(TypedDict, total=False):
    model_name: Required[str]
    """Model name from the model provider."""

    router: Required[int]
    """ID of the model to create the provider for (router ID, eg. 123)."""

    type: Required[ProviderType]
    """Model provider type."""

    key: Optional[str]
    """Model provider API key."""

    model_active_params: int
    """
    Active params of the model in billions of parameters for carbon footprint
    computation. For more information, see https://ecologits.ai
    """

    model_hosting_zone: ProviderCarbonFootprintZone
    """
    Model hosting zone using ISO 3166-1 alpha-3 code format (e.g., `WOR` for World,
    `FRA` for France, `USA` for United States). This determines the electricity mix
    used for carbon intensity calculations. For more information, see
    https://ecologits.ai
    """

    model_total_params: int
    """
    Total params of the model in billions of parameters for carbon footprint
    computation. For more information, see https://ecologits.ai
    """

    qos_limit: Optional[float]
    """The value to use for the quality of service.

    Depends of the metric, the value can be a percentile, a threshold, etc.
    """

    qos_metric: Optional[Metric]
    """The metric to use for the quality of service policy.

    If not provided, no QoS policy is applied.
    """

    api_timeout: Annotated[int, PropertyInfo(alias="timeout")]
    """
    Timeout for the model provider requests, after user receive an 503 error (model
    is too busy).
    """

    url: Optional[str]
    """Model provider API url.

    The url must only contain the domain name (without `/v1` suffix for example).
    Depends of the model provider type, the url can be optional (Albert, OpenAI).
    """
