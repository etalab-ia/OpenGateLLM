from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_validator

from api.domain import BaseModel
from api.domain.router.entities import DEFAULT_QOS_HEALTH_THRESHOLDS, RouterLoadBalancingStrategy, RouterQosMetric, RouterQosMode
from api.infrastructure.fastapi.schemas import UnixTimestamp
from api.schemas.models import ModelType


class CreateRouterBody(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(description="Name of the model router.", examples=["model-router-1"])]  # fmt: off
    router_type: Annotated[ModelType, Field(alias="type", description="Type of the model router. It will be used to identify the model router type.", examples=["text-generation"])]  # fmt: off
    aliases: Annotated[list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]], Field(default_factory=list, description="Aliases of the model. It will be used to identify the model by users.", examples=[["model-alias", "model-alias-2"]])]  # fmt: off
    load_balancing_strategy: Annotated[RouterLoadBalancingStrategy, Field(default=RouterLoadBalancingStrategy.SHUFFLE, description="Routing strategy for load balancing between providers of the model. It will be used to identify the model type.")]  # fmt: off
    qos_mode: Annotated[RouterQosMode, Field(default=RouterQosMode.WAIT, description="QoS admission mode. `off` disables admission; `wait` retries when providers are full.")]  # fmt: off
    qos_retry: Annotated[int, Field(default=10, ge=0, description="Max number of try_admit retries after the first FULL response when qos_mode is wait.")]  # fmt: off
    qos_metric: Annotated[RouterQosMetric, Field(default=RouterQosMetric.INFLIGHT, description="Metric used for QoS load accounting.")]  # fmt: off
    qos_health_thresholds: Annotated[list[float], Field(default_factory=lambda: list(DEFAULT_QOS_HEALTH_THRESHOLDS), min_length=2, max_length=2, description="Saturation thresholds [orange, red] as load/qos_limit ratios.")]  # fmt: off
    cost_prompt_tokens: Annotated[float, Field(default=0.0, ge=0.0, description="Cost of a million prompt tokens (decrease user budget)")]
    cost_completion_tokens: Annotated[float, Field(default=0.0, ge=0.0, description="Cost of a million completion tokens (decrease user budget)")]

    @field_validator("qos_health_thresholds")
    @classmethod
    def validate_qos_health_thresholds(cls, value: list[float]) -> list[float]:
        if value[0] > value[1]:
            raise ValueError("qos_health_thresholds[0] (orange) must be <= qos_health_thresholds[1] (red)")
        return value


class UpdateRouterBody(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(..., description="Name of the model router.", examples=["model-router-1"])]  # fmt: off
    router_type: Annotated[ModelType, Field(..., description="Type of the model router. It will be used to identify the model router type.", examples=["text-generation"], alias="type")]  # fmt: off
    aliases: Annotated[list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]], Field(..., description="Aliases of the model replacing the current ones. It will be used to identify the model by users. An empty list removes all the aliases.", examples=[["model-alias", "model-alias-2"]])]  # fmt: off
    load_balancing_strategy: Annotated[RouterLoadBalancingStrategy, Field(..., description="Routing strategy for load balancing between providers of the model. It will be used to identify the model type.", examples=["least_busy"])]  # fmt: off
    qos_mode: Annotated[RouterQosMode, Field(..., description="QoS admission mode. `off` disables admission; `wait` retries when providers are full.")]  # fmt: off
    qos_retry: Annotated[int, Field(..., ge=0, description="Max number of try_admit retries after the first FULL response when qos_mode is wait.")]  # fmt: off
    qos_metric: Annotated[RouterQosMetric, Field(..., description="Metric used for QoS load accounting.")]  # fmt: off
    qos_health_thresholds: Annotated[list[float], Field(..., min_length=2, max_length=2, description="Saturation thresholds [orange, red] as load/qos_limit ratios.")]  # fmt: off
    cost_prompt_tokens: Annotated[float, Field(..., ge=0.0, description="Cost of a million prompt tokens (decrease user budget)")]
    cost_completion_tokens: Annotated[float, Field(..., ge=0.0, description="Cost of a million completion tokens (decrease user budget)")]  # fmt: off

    @field_validator("qos_health_thresholds")
    @classmethod
    def validate_qos_health_thresholds(cls, value: list[float]) -> list[float]:
        if value[0] > value[1]:
            raise ValueError("qos_health_thresholds[0] (orange) must be <= qos_health_thresholds[1] (red)")
        return value


class RouterResponse(BaseModel):
    object: Annotated[Literal["router"], Field(default="router", description="Type of the object.")]
    id: Annotated[int, Field(description="ID of the router.")]
    name: Annotated[str, Field(description="Name of the router.")]
    user_id: Annotated[int, Field(description="ID of the user that owns the router.")]
    router_type: Annotated[ModelType, Field(alias="type", description="Type of the model router. It will be used to identify the model router type.", examples=["text-generation"])]  # fmt: off
    aliases: Annotated[list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]], Field(description="Aliases of the model. It will be used to identify the model by users.", examples=[["model-alias", "model-alias-2"]])]  # fmt: off
    load_balancing_strategy: Annotated[RouterLoadBalancingStrategy, Field(description="Routing strategy for load balancing between providers of the model. It will be used to identify the model type.", examples=["least_busy"])]  # fmt: off
    qos_mode: Annotated[RouterQosMode, Field(description="QoS admission mode.")]
    qos_retry: Annotated[int, Field(description="Max number of try_admit retries after the first FULL response when qos_mode is wait.")]
    qos_metric: Annotated[RouterQosMetric, Field(description="Metric used for QoS load accounting.")]
    qos_health_thresholds: Annotated[list[float], Field(description="Saturation thresholds [orange, red] as load/qos_limit ratios.")]
    cost_prompt_tokens: Annotated[float, Field(description="Cost of a million prompt tokens (decrease user budget)")]
    cost_completion_tokens: Annotated[float, Field(description="Cost of a million completion tokens (decrease user budget)")]
    providers: Annotated[int, Field(default=0, description="Number of providers in the router.")]
    created: Annotated[UnixTimestamp, Field(description="Time of creation, as Unix timestamp.")]
    updated: Annotated[UnixTimestamp, Field(description="Time of last update, as Unix timestamp.")]


class RoutersResponse(BaseModel):
    object: Annotated[Literal["list"], Field(default="list", description="Type of the object.")]
    total: Annotated[int, Field(description="Total number of routers.")]
    offset: Annotated[int, Field(description="Offset of the routers list.")]
    limit: Annotated[int, Field(description="Limit of the routers list.")]
    data: Annotated[list[RouterResponse], Field(description="List of routers.")]
