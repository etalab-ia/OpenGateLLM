from enum import Enum
from typing import Literal

import pycountry
from pydantic import Field, constr, model_validator

from api.schemas import BaseModel
from api.schemas.core.metrics import Metric
from api.utils.variables import DEFAULT_TIMEOUT

# Add world as a country code, default value of the carbon footprint computation framework
country_codes = [country.alpha_3 for country in pycountry.countries] + ["WOR"]
country_codes_dict = {str(code).upper(): str(code) for code in sorted(set(country_codes))}
ProviderCarbonFootprintZone = Enum("ProviderCarbonFootprintZone", country_codes_dict, type=str)


class ProviderType(str, Enum):
    ALBERT = "albert"
    OPENAI = "openai"
    MISTRAL = "mistral"
    TEI = "tei"
    VLLM = "vllm"


class CreateProvider(BaseModel):
    router: int = Field(..., description="ID of the model to create the provider for (router ID, eg. 123).")  # fmt: off
    type: ProviderType = Field(..., description="Model provider type.")  # fmt: off
    url: constr(strip_whitespace=True, min_length=1) | None = Field(default=None, description="Model provider API url. The url must only contain the domain name (without `/v1` suffix for example). Depends of the model provider type, the url can be optional (Albert, OpenAI).")  # fmt: off
    key: constr(strip_whitespace=True, min_length=1) | None = Field(default=None, description="Model provider API key.")  # fmt: off
    timeout: int = Field(default=DEFAULT_TIMEOUT, description="Timeout for the model provider requests, after user receive an 503 error (model is too busy).")  # fmt: off
    model_name: str = Field(..., description="Model name from the model provider.")  # fmt: off
    model_carbon_footprint_zone: ProviderCarbonFootprintZone = Field(default=ProviderCarbonFootprintZone.WOR, description="Model hosting zone using ISO 3166-1 alpha-3 code format (e.g., `WOR` for World, `FRA` for France, `USA` for United States). This determines the electricity mix used for carbon intensity calculations. For more information, see https://ecologits.ai")  # fmt: off
    model_carbon_footprint_total_params: int = Field(default=0, ge=0, description="Total params of the model in billions of parameters for carbon footprint computation. For more information, see https://ecologits.ai")  # fmt: off
    model_carbon_footprint_active_params: int = Field(default=0, ge=0, description="Active params of the model in billions of parameters for carbon footprint computation. For more information, see https://ecologits.ai")  # fmt: off
    qos_metric: Metric | None = Field(default=None, description="The metric to use for the quality of service policy. If not provided, no QoS policy is applied.")  # fmt: off
    qos_limit: float | None = Field(default=None, ge=0.0, description="The value to use for the quality of service. Depends of the metric, the value can be a percentile, a threshold, etc.")  # fmt: off

    @model_validator(mode="after")
    def format_provider(self):
        if self.qos_metric is not None and self.qos_limit is None:
            raise ValueError("QoS value is required if QoS metric is provided.")

        if self.url is None:
            if self.type == ProviderType.ALBERT:
                self.url = "https://albert.api.etalab.gouv.fr/"
            elif self.type == ProviderType.MISTRAL:
                self.url = "https://albert.api.etalab.gouv.fr/"
            elif self.type == ProviderType.OPENAI:
                self.url = "https://api.openai.com/"
            else:
                raise ValueError("URL is required for this model provider type.")

        elif not self.url.endswith("/"):
            self.url = f"{self.url}/"

        return self


class CreateProviderResponse(BaseModel):
    id: int = Field(..., description="ID of the created provider.")  # fmt: off


class UpdateProvider(BaseModel):
    router: int | None = Field(default=None, description="The ID of the new router to assign to the provider.")  # fmt: off
    timeout: int | None = Field(default=None, description="Timeout for the model provider requests, after user receive an 500 error (model is too busy).")  # fmt: off
    model_carbon_footprint_zone: ProviderCarbonFootprintZone | None = Field(default=None, description="Model hosting zone using ISO 3166-1 alpha-3 code format (e.g., `WOR` for World, `FRA` for France, `USA` for United States). This determines the electricity mix used for carbon intensity calculations. For more information, see https://ecologits.ai")  # fmt: off
    model_carbon_footprint_total_params: int | None = Field(default=None, ge=0, description="Total params of the model in billions of parameters for carbon footprint computation. If not provided, the active params will be used if provided, else carbon footprint will not be computed. For more information, see https://ecologits.ai")  # fmt: off
    model_carbon_footprint_active_params: int | None = Field(default=None, ge=0, description="Active params of the model in billions of parameters for carbon footprint computation. If not provided, the total params will be used if provided, else carbon footprint will not be computed. For more information, see https://ecologits.ai")  # fmt: off
    qos_metric: Metric | None = Field(default=None, description="The metric to use for the quality of service policy. If not provided, no QoS policy is applied.")  # fmt: off
    qos_limit: float | None = Field(default=None, ge=0.0, description="The value to use for the quality of service. Depends of the metric, the value can be a percentile, a threshold, etc.")  # fmt: off

    @model_validator(mode="after")
    def validate_model(self):
        if self.qos_metric is not None and self.qos_limit is None:
            raise ValueError("QoS value is required if QoS metric is provided.")

        return self


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
    model_carbon_footprint_zone: ProviderCarbonFootprintZone = Field(default=ProviderCarbonFootprintZone.WOR, description="Model hosting zone using ISO 3166-1 alpha-3 code format (e.g., `WOR` for World, `FRA` for France, `USA` for United States). This determines the electricity mix used for carbon intensity calculations. For more information, see https://ecologits.ai", examples=["WOR"])  # fmt: off
    model_carbon_footprint_total_params: int = Field(default=0, ge=0, description="Total params of the model in billions of parameters for carbon footprint computation. If not provided, the active params will be used if provided, else carbon footprint will not be computed. For more information, see https://ecologits.ai")  # fmt: off
    model_carbon_footprint_active_params: int = Field(default=0, ge=0, description="Active params of the model in billions of parameters for carbon footprint computation. If not provided, the total params will be used if provided, else carbon footprint will not be computed. For more information, see https://ecologits.ai")  # fmt: off
    qos_metric: Metric | None = Field(description="The metric to use for the QoS policy. If not provided, no QoS policy is applied.")  # fmt: off
    qos_limit: float | None = Field(default=None, ge=0.0, description="The value to use for the quality of service. Depends of the metric, the value can be a percentile, a threshold, etc.")  # fmt: off
    created: int | None = Field(default=None, description="Time of creation, as Unix timestamp.")  # fmt: off
    updated: int | None = Field(default=None, description="Time of last update, as Unix timestamp.")  # fmt: off


class Providers(BaseModel):
    object: Literal["list"] = "list"
    data: list[Provider]
