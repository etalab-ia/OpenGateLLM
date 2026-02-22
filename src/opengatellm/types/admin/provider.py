# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

import builtins
from typing import TYPE_CHECKING, Dict, Optional
from typing_extensions import Literal

from pydantic import Field as FieldInfo

from .metric import Metric
from ..._models import BaseModel
from .provider_type import ProviderType
from .provider_carbon_footprint_zone import ProviderCarbonFootprintZone

__all__ = ["Provider"]


class Provider(BaseModel):
    id: int
    """Provider ID."""

    key: Optional[str] = None
    """Provider API key."""

    api_model_name: str = FieldInfo(alias="model_name")
    """Model name from the model provider."""

    qos_metric: Optional[Metric] = None
    """The metric to use for the QoS policy.

    If not provided, no QoS policy is applied.
    """

    router_id: int
    """ID of the router that owns the provider."""

    timeout: int
    """
    Timeout for the provider requests, after user receive an 500 error (model is too
    busy).
    """

    type: ProviderType
    """Provider type."""

    user_id: int
    """ID of the user that owns the provider."""

    created: Optional[int] = None
    """Time of creation, as Unix timestamp."""

    api_model_active_params: Optional[int] = FieldInfo(alias="model_active_params", default=None)
    """
    Active params of the model in billions of parameters for carbon footprint
    computation. If not provided, the total params will be used if provided, else
    carbon footprint will not be computed. For more information, see
    https://ecologits.ai
    """

    api_model_hosting_zone: Optional[ProviderCarbonFootprintZone] = FieldInfo(alias="model_hosting_zone", default=None)
    """
    Model hosting zone using ISO 3166-1 alpha-3 code format (e.g., `WOR` for World,
    `FRA` for France, `USA` for United States). This determines the electricity mix
    used for carbon intensity calculations. For more information, see
    https://ecologits.ai
    """

    api_model_total_params: Optional[int] = FieldInfo(alias="model_total_params", default=None)
    """
    Total params of the model in billions of parameters for carbon footprint
    computation. If not provided, the active params will be used if provided, else
    carbon footprint will not be computed. For more information, see
    https://ecologits.ai
    """

    object: Optional[Literal["provider"]] = None

    qos_limit: Optional[float] = None
    """The value to use for the quality of service.

    Depends of the metric, the value can be a percentile, a threshold, etc.
    """

    updated: Optional[int] = None
    """Time of last update, as Unix timestamp."""

    url: Optional[str] = None
    """Provider API url.

    The url must only contain the domain name (without `/v1` suffix for example).
    """

    if TYPE_CHECKING:
        # Some versions of Pydantic <2.8.0 have a bug and don’t allow assigning a
        # value to this field, so for compatibility we avoid doing it at runtime.
        __pydantic_extra__: Dict[str, builtins.object] = FieldInfo(init=False)  # pyright: ignore[reportIncompatibleVariableOverride]

        # Stub to indicate that arbitrary properties are accepted.
        # To access properties that are not valid identifiers you can use `getattr`, e.g.
        # `getattr(obj, '$type')`
        def __getattr__(self, attr: str) -> builtins.object: ...
    else:
        __pydantic_extra__: Dict[str, builtins.object]
