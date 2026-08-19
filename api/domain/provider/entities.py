from enum import StrEnum
from http import HTTPMethod
from typing import Annotated, Literal

import pycountry
from pydantic import Field, model_validator

from api.domain import BaseModel, EntitiesPage, ForwardablePayload
from api.domain.model.entities import ModelJsonResponse, ModelType
from api.domain.router.entities import Router
from api.utils.variables import EndpointRoute

# Add world as a country code, default value of the carbon footprint computation framework
country_codes = [country.alpha_3 for country in pycountry.countries] + ["WOR"]
HostingZone = StrEnum("HostingZone", {str(code).upper(): str(code) for code in sorted(set(country_codes))})


class Metric(StrEnum):
    LATENCY = "latency"  # requests latency
    TTFT = "ttft"  # time to first token
    NORMALIZED_LATENCY = "normalized_latency"  # intended as latency per completion token, but the raw latency is written as is (never normalized)


class QoSMetric(StrEnum):
    TTFT = "ttft"  # time to first token
    LATENCY = "latency"  # requests latency
    INFLIGHT = "inflight"  # requests concurrency
    PERFORMANCE = "performance"  # custom performance metric


class BasicAuth(BaseModel):
    username: str
    password: str


class ProviderType(StrEnum):
    ALBERT = "albert"
    OPENAI = "openai"
    MISTRAL = "mistral"
    TEI = "tei"
    VLLM = "vllm"

    def is_compatible_with(self, router_type: ModelType) -> bool:
        return self.value in COMPATIBLE_PROVIDER_TYPES[router_type]


COMPATIBLE_PROVIDER_TYPES: dict[ModelType, list[str]] = {
    ModelType.AUTOMATIC_SPEECH_RECOGNITION: [  # audio transcriptions
        ProviderType.ALBERT.value,
        ProviderType.MISTRAL.value,
        ProviderType.OPENAI.value,
        ProviderType.VLLM.value,
    ],
    ModelType.IMAGE_TEXT_TO_TEXT: [  # chat completions
        ProviderType.ALBERT.value,
        ProviderType.MISTRAL.value,
        ProviderType.OPENAI.value,
        ProviderType.VLLM.value,
    ],
    ModelType.TEXT_EMBEDDINGS_INFERENCE: [  # embeddings
        ProviderType.ALBERT.value,
        ProviderType.OPENAI.value,
        ProviderType.MISTRAL.value,
        ProviderType.TEI.value,
        ProviderType.VLLM.value,
    ],
    ModelType.TEXT_GENERATION: [  # chat completions
        ProviderType.ALBERT.value,
        ProviderType.MISTRAL.value,
        ProviderType.OPENAI.value,
        ProviderType.VLLM.value,
    ],
    ModelType.TEXT_CLASSIFICATION: [  # rerank
        ProviderType.ALBERT.value,
        ProviderType.TEI.value,
        ProviderType.VLLM.value,
    ],
    ModelType.IMAGE_TO_TEXT: [  # ocr
        ProviderType.MISTRAL.value,
    ],
}


class ProviderSortField(StrEnum):
    ID = "id"
    MODEL_NAME = "model_name"
    CREATED = "created"


ProviderPage = EntitiesPage["Provider"]


class Provider(BaseModel):
    id: int
    router_id: int
    user_id: int
    type: ProviderType
    url: str
    key: str | None = None
    basic_auth: BasicAuth | None = None
    timeout: int
    model_name: str
    model_hosting_zone: HostingZone = HostingZone.WOR
    model_total_params: int = 0
    model_active_params: int = 0
    qos_metric: QoSMetric | None = None
    qos_limit: float | None = None
    max_context_length: int | None = None
    vector_size: int | None = None
    created: int
    updated: int

    def with_router_id(self, router_id: int) -> "Provider":
        return self.model_copy(update={"router_id": router_id})

    def with_timeout(self, timeout: int) -> "Provider":
        return self.model_copy(update={"timeout": timeout})

    def with_model_hosting_zone(self, model_hosting_zone: HostingZone) -> "Provider":
        return self.model_copy(update={"model_hosting_zone": model_hosting_zone})

    def with_model_total_params(self, model_total_params: int) -> "Provider":
        return self.model_copy(update={"model_total_params": model_total_params})

    def with_model_active_params(self, model_active_params: int) -> "Provider":
        return self.model_copy(update={"model_active_params": model_active_params})

    def with_qos_metric(self, qos_metric: QoSMetric | None) -> "Provider":
        return self.model_copy(update={"qos_metric": qos_metric})

    def with_qos_limit(self, qos_limit: float | None) -> "Provider":
        return self.model_copy(update={"qos_limit": qos_limit})

    def with_max_context_length(self, max_context_length: int | None) -> "Provider":
        return self.model_copy(update={"max_context_length": max_context_length})

    def with_vector_size(self, vector_size: int | None) -> "Provider":
        return self.model_copy(update={"vector_size": vector_size})

    def is_compatible_with(self, router: Router) -> bool:
        return self.type.is_compatible_with(router.type)


class ProviderCapabilities(BaseModel):
    max_context_length: int | None
    vector_size: int | None = None


class ProviderOriginalRequest(BaseModel):
    endpoint: Annotated[EndpointRoute, Field(description="The source endpoint (at the user side) of the request.")]
    payload: Annotated[ForwardablePayload | None, Field(default=None, description="The payload to use for the request.")]


class ResponseMetrics(BaseModel):
    latency: Annotated[int, Field(default=0, description="The latency of the response.")]
    ttft: Annotated[int | None, Field(default=None, description="The time to first byte of the response.")]


class ProviderFormattedRequest(BaseModel):
    method: Annotated[HTTPMethod, Field(description="The HTTP method to build the request.")]
    url: Annotated[str, Field(description="The model API URL to build the request.")]
    auth: Annotated[BasicAuth | None, Field(default=None, description="The authentication to use for the request.")]
    body: Annotated[dict, Field(default={}, description="The JSON body to use for the request.")]
    form: Annotated[dict, Field(default={}, description="The form-encoded data to use for the request.")]
    files: Annotated[dict, Field(default={}, description="The files to use for the request.")]


class ProviderOriginalResponse(BaseModel):
    data: Annotated[dict | list | None, Field(default=None, description="The JSON data to use for the response.")]
    text: Annotated[str | None, Field(default=None, description="The text data to use for the response.")]


class ProviderMetrics(ModelJsonResponse):
    object: Literal["providerMetrics"] = "providerMetrics"
    waiting_requests: float
    running_requests: float


class ProviderFormattedResponse(BaseModel):
    id: Annotated[str, Field(description="The request identifier.")]
    data: Annotated[ModelJsonResponse | None, Field(default=None, description="The JSON data to use for the response.")]
    text: Annotated[str | None, Field(default=None, description="The text data to use for the response.")]

    @model_validator(mode="after")
    def validate_data_and_text(self) -> "ProviderFormattedResponse":
        if self.data is not None and self.text is not None:
            raise ValueError("data and text cannot be set at the same time")

        if self.data is None and self.text is None:
            raise ValueError("data and text cannot be None at the same time")

        return self

    def get_completions(self) -> list[str]:
        if self.data is not None:
            return self.data.get_completions()
        else:
            return [self.text.strip()]
