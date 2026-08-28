from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from api.domain import BaseModel
from api.domain.provider.entities import BasicAuth, HostingZone, Provider, ProviderType, QoSMetric
from api.schemas.core.configuration import ModelProvider


class CreateProviderBody(ModelProvider):
    router_id: Annotated[int, Field(..., description="ID of the model to create the provider for (router ID, eg. 123).")]


class CreateProviderResponse(BaseModel):
    id: Annotated[int, Field(..., description="Provider ID.")]
    router_id: Annotated[int, Field(..., description="ID of the router that owns the provider.")]
    user_id: Annotated[int, Field(..., description="ID of the user that owns the provider.")]
    type: Annotated[ProviderType, Field(..., description="Provider type.")]
    url: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, to_lower=True), Field(default=None, description="Provider API url. The url must only contain the domain name (without `/v1` suffix for example).")]  # fmt: off
    key: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1), Field(default=None, description="Provider API key.")]  # fmt: off
    basic_auth: Annotated[BasicAuth | None, Field(default=None, description="Provider basic authentication.")]
    timeout: Annotated[int, Field(..., ge=1, le=3600, description="Timeout for the provider requests, after user receive an 500 error (model is too busy).")]  # fmt: off
    model_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(..., description="Model name from the model provider.")]  # fmt: off
    model_hosting_zone: Annotated[HostingZone, Field(default=HostingZone.WOR, description="Model hosting zone using ISO 3166-1 alpha-3 code format (e.g., `WOR` for World, `FRA` for France, `USA` for United States). This determines the electricity mix used for carbon intensity calculations. For more information, see https://ecologits.ai", examples=["WOR"])]  # fmt: off
    model_total_params: Annotated[int, Field(default=0, ge=0, description="Total params of the model in billions of parameters for carbon footprint computation. If not provided, the active params will be used if provided, else carbon footprint will not be computed. For more information, see https://ecologits.ai")]  # fmt: off
    model_active_params: Annotated[int, Field(default=0, ge=0, description="Active params of the model in billions of parameters for carbon footprint computation. If not provided, the total params will be used if provided, else carbon footprint will not be computed. For more information, see https://ecologits.ai")]  # fmt: off
    qos_metric: Annotated[QoSMetric | None, Field(default=None, description="The metric to use for the QoS policy. If not provided, no QoS policy is applied.")]  # fmt: off
    qos_limit: Annotated[float | None, Field(default=None, ge=0.0, description="The value to use for the quality of service. Depends of the metric, the value can be a percentile, a threshold, etc.")]  # fmt: off
    created: Annotated[int | None, Field(default=None, description="Time of creation, as Unix timestamp.")]  # fmt: off
    updated: Annotated[int | None, Field(default=None, description="Time of last update, as Unix timestamp.")]  # fmt: off

    @model_validator(mode="before")
    @classmethod
    def from_provider(cls, data):
        if isinstance(data, Provider):
            return {
                "id": data.id,
                "router_id": data.router_id,
                "user_id": data.user_id,
                "type": data.type,
                "url": data.url,
                "key": data.key,
                "basic_auth": data.basic_auth,
                "timeout": data.timeout,
                "model_name": data.model_name,
                "model_hosting_zone": data.model_hosting_zone,
                "model_total_params": data.model_total_params,
                "model_active_params": data.model_active_params,
                "qos_metric": data.qos_metric,
                "qos_limit": data.qos_limit,
                "created": int(data.created.timestamp()),
                "updated": int(data.updated.timestamp()),
            }
        return data


class UpdateProviderBody(BaseModel):
    router_id: Annotated[int, Field(..., description="The ID of the router to assign to the provider.")]  # fmt: off
    timeout: Annotated[int, Field(..., ge=1, le=3600, description="Timeout for the model provider requests, after user receive an 500 error (model is too busy).")]  # fmt: off
    model_hosting_zone: Annotated[HostingZone, Field(..., description="Model hosting zone using ISO 3166-1 alpha-3 code format (e.g., `WOR` for World, `FRA` for France, `USA` for United States). This determines the electricity mix used for carbon intensity calculations. For more information, see https://ecologits.ai")]  # fmt: off
    model_total_params: Annotated[int, Field(..., ge=0, description="Total params of the model in billions of parameters for carbon footprint computation. If 0, the active params will be used if provided, else carbon footprint will not be computed. For more information, see https://ecologits.ai")]  # fmt: off
    model_active_params: Annotated[int, Field(..., ge=0, description="Active params of the model in billions of parameters for carbon footprint computation. If 0, the total params will be used if provided, else carbon footprint will not be computed. For more information, see https://ecologits.ai")]  # fmt: off
    qos_metric: Annotated[QoSMetric | None, Field(..., description="The metric to use for the quality of service policy. If null, no QoS policy is applied.")]  # fmt: off
    qos_limit: Annotated[float | None, Field(..., ge=0.0, description="The value to use for the quality of service. Depends of the metric, the value can be a percentile, a threshold, etc. If null, no QoS policy is applied.")]  # fmt: off

    @model_validator(mode="after")
    def validate_model(self):
        if self.qos_metric is not None and self.qos_limit is None:
            raise ValueError("QoS value is required if QoS metric is provided.")

        return self


class ProviderResponse(BaseModel):
    object: Annotated[Literal["provider"], Field(default="provider", description="Type of the object.")]
    id: Annotated[int, Field(description="provider ID.")]  # fmt: off
    router_id: Annotated[int, Field(description="ID of the router that owns the provider.")]  # fmt: off
    user_id: Annotated[int, Field(description="ID of the user that owns the provider.")]  # fmt: off
    provider_type: Annotated[ProviderType, Field(alias="type", description="Provider type.")]  # fmt: off
    url: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, to_lower=True), Field(default=None, description="provider API url. The url must only contain the domain name (without `/v1` suffix for example).")]  # fmt: off
    timeout: Annotated[int, Field(description="Timeout for the provider requests, after user receive an 500 error (model is too busy).")]
    model_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(description="Model name from the model provider.")]
    model_hosting_zone: Annotated[HostingZone, Field(default=HostingZone.WOR, description="Model hosting zone using ISO 3166-1 alpha-3 code format (e.g., `WOR` for World, `FRA` for France, `USA` for United States). This determines the electricity mix used for carbon intensity calculations. For more information, see https://ecologits.ai", examples=["WOR"])]  # fmt: off
    model_total_params: Annotated[int, Field(default=0, ge=0, description="Total params of the model in billions of parameters for carbon footprint computation. If not provided, the active params will be used if provided, else carbon footprint will not be computed. For more information, see https://ecologits.ai")]  # fmt: off
    model_active_params: Annotated[int, Field(default=0, ge=0, description="Active params of the model in billions of parameters for carbon footprint computation. If not provided, the total params will be used if provided, else carbon footprint will not be computed. For more information, see https://ecologits.ai")]  # fmt: off
    qos_metric: Annotated[QoSMetric | None, Field(description="The metric to use for the QoS policy. If not provided, no QoS policy is applied.")]
    qos_limit: Annotated[float | None, Field(default=None, ge=0.0, description="The value to use for the quality of service. Depends of the metric, the value can be a percentile, a threshold, etc.")]  # fmt: off
    max_context_length: Annotated[int | None, Field(default=None, description="Maximum amount of tokens a context could contains, probed on the provider API. It is the same for all the providers of a router.")]  # fmt: off
    vector_size: Annotated[int | None, Field(default=None, description="Dimension of the vectors, probed on the provider API for embeddings models only. It is the same for all the providers of a router.")]  # fmt: off
    created: Annotated[int | None, Field(default=None, description="Time of creation, as Unix timestamp.")]
    updated: Annotated[int | None, Field(default=None, description="Time of last update, as Unix timestamp.")]

    @model_validator(mode="before")
    @classmethod
    def from_provider(cls, data):
        if isinstance(data, Provider):
            return {
                "object": "provider",
                "id": data.id,
                "router_id": data.router_id,
                "user_id": data.user_id,
                "type": data.type,
                "url": data.url,
                "timeout": data.timeout,
                "model_name": data.model_name,
                "model_hosting_zone": data.model_hosting_zone,
                "model_total_params": data.model_total_params,
                "model_active_params": data.model_active_params,
                "qos_metric": data.qos_metric,
                "qos_limit": data.qos_limit,
                "max_context_length": data.max_context_length,
                "vector_size": data.vector_size,
                "created": int(data.created.timestamp()),
                "updated": int(data.updated.timestamp()),
            }
        return data


class ProvidersResponse(BaseModel):
    object: Annotated[Literal["list"], Field(default="list", description="Type of the object.")]
    total: Annotated[int, Field(description="Total number of providers.")]
    offset: Annotated[int, Field(description="Offset of the providers list.")]
    limit: Annotated[int, Field(description="Limit of the providers list.")]
    data: Annotated[list[ProviderResponse], Field(description="List of providers.")]
