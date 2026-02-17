from enum import Enum
from typing import Literal

import pycountry
from pydantic import Field, constr

from api.domain.model.entities import ModelType
from api.schemas import BaseModel
from api.schemas.core.models import Metric

# Add world as a country code, default value of the carbon footprint computation framework
country_codes = [country.alpha_3 for country in pycountry.countries] + ["WOR"]
country_codes_dict = {str(code).upper(): str(code) for code in sorted(set(country_codes))}
ProviderCarbonFootprintZone: type[Enum] = Enum("ProviderCarbonFootprintZone", country_codes_dict, type=str)


class ProviderType(str, Enum):
    ALBERT = "albert"
    OPENAI = "openai"
    MISTRAL = "mistral"
    TEI = "tei"
    VLLM = "vllm"


COMPATIBLE_PROVIDER_TYPES: dict[ModelType, list[str]] = {
    ModelType.AUTOMATIC_SPEECH_RECOGNITION: [
        ProviderType.ALBERT.value,
        ProviderType.MISTRAL.value,
        ProviderType.OPENAI.value,
        ProviderType.VLLM.value,
    ],
    ModelType.IMAGE_TEXT_TO_TEXT: [
        ProviderType.ALBERT.value,
        ProviderType.MISTRAL.value,
        ProviderType.OPENAI.value,
        ProviderType.VLLM.value,
    ],
    ModelType.TEXT_EMBEDDINGS_INFERENCE: [
        ProviderType.ALBERT.value,
        ProviderType.OPENAI.value,
        ProviderType.TEI.value,
        ProviderType.VLLM.value,
    ],
    ModelType.TEXT_GENERATION: [
        ProviderType.ALBERT.value,
        ProviderType.MISTRAL.value,
        ProviderType.OPENAI.value,
        ProviderType.VLLM.value,
    ],
    ModelType.TEXT_CLASSIFICATION: [
        ProviderType.ALBERT.value,
        ProviderType.TEI.value,
    ],
    ModelType.IMAGE_TO_TEXT: [
        ProviderType.MISTRAL.value,
    ],
}


class Provider(BaseModel):
    object: Literal["provider"] = "provider"
    id: int = Field(..., description="Provider ID.")  # fmt: off
    router_id: int = Field(..., description="ID of the router that owns the provider.")  # fmt: off
    user_id: int = Field(..., description="ID of the user that owns the provider.")  # fmt: off
    type: ProviderType = Field(..., description="Provider type.")  # fmt: off
    url: constr(strip_whitespace=True, min_length=1, to_lower=True) | None = Field(default=None, description="Provider API url. The url must only contain the domain name (without `/v1` suffix for example).")  # fmt: off
    key: str | None = Field(description="Provider API key.")  # fmt: off
    timeout: int = Field(..., description="Timeout for the provider requests, after user receive an 500 error (model is too busy).")  # fmt: off
    model_name: str = Field(..., description="Model name from the model provider.")  # fmt: off
    model_hosting_zone: ProviderCarbonFootprintZone = Field(default=ProviderCarbonFootprintZone.WOR, description="Model hosting zone using ISO 3166-1 alpha-3 code format (e.g., `WOR` for World, `FRA` for France, `USA` for United States). This determines the electricity mix used for carbon intensity calculations. For more information, see https://ecologits.ai", examples=["WOR"])  # fmt: off
    model_total_params: int = Field(default=0, ge=0, description="Total params of the model in billions of parameters for carbon footprint computation. If not provided, the active params will be used if provided, else carbon footprint will not be computed. For more information, see https://ecologits.ai")  # fmt: off
    model_active_params: int = Field(default=0, ge=0, description="Active params of the model in billions of parameters for carbon footprint computation. If not provided, the total params will be used if provided, else carbon footprint will not be computed. For more information, see https://ecologits.ai")  # fmt: off
    qos_metric: Metric | None = Field(description="The metric to use for the QoS policy. If not provided, no QoS policy is applied.")  # fmt: off
    qos_limit: float | None = Field(default=None, ge=0.0, description="The value to use for the quality of service. Depends of the metric, the value can be a percentile, a threshold, etc.")  # fmt: off
    created: int | None = Field(default=None, description="Time of creation, as Unix timestamp.")  # fmt: off
    updated: int | None = Field(default=None, description="Time of last update, as Unix timestamp.")  # fmt: off
