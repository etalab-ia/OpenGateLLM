from enum import Enum
from typing import Literal

from pydantic import Field, constr

from api.schemas import BaseModel
from api.schemas.models import ModelType


class RouterLoadBalancingStrategy(str, Enum):
    SHUFFLE = "shuffle"
    LEAST_BUSY = "least_busy"


class CreateRouter(BaseModel):
    name: constr(strip_whitespace=True, min_length=1) = Field(..., description="Name of the model router.", examples=["model-router-1"])  # fmt: off
    type: ModelType = Field(..., description="Type of the model router. It will be used to identify the model router type.", examples=["text-generation"])  # fmt: off
    aliases: list[constr(strip_whitespace=True, min_length=1, max_length=64)] = Field(default_factory=list, description="Aliases of the model. It will be used to identify the model by users.", examples=[["model-alias", "model-alias-2"]])  # fmt: off
    load_balancing_strategy: RouterLoadBalancingStrategy = Field(default=RouterLoadBalancingStrategy.SHUFFLE, description="Routing strategy for load balancing between providers of the model. It will be used to identify the model type.", examples=["least_busy"])  # fmt: off
    cost_prompt_tokens: float = Field(default=0.0, ge=0.0, description="Cost of a million prompt tokens (decrease user budget)")
    cost_completion_tokens: float = Field(default=0.0, ge=0.0, description="Cost of a million completion tokens (decrease user budget)")


class CreateRouterResponse(BaseModel):
    id: int = Field(..., description="ID of the created router.")  # fmt: off
    name: constr(strip_whitespace=True, min_length=1) = Field(..., description="Name of the model router.",
                                                              examples=["model-router-1"])  # fmt: off
    type: ModelType = Field(...,
                            description="Type of the model router. It will be used to identify the model router type.",
                            examples=["text-generation"])  # fmt: off
    aliases: list[constr(strip_whitespace=True, min_length=1, max_length=64)] = Field(default_factory=list,
                                                                                      description="Aliases of the model. It will be used to identify the model by users.",
                                                                                      examples=[["model-alias",
                                                                                                 "model-alias-2"]])  # fmt: off
    load_balancing_strategy: RouterLoadBalancingStrategy = Field(default=RouterLoadBalancingStrategy.SHUFFLE,
                                                                 description="Routing strategy for load balancing between providers of the model. It will be used to identify the model type.",
                                                                 examples=["least_busy"])  # fmt: off
    cost_prompt_tokens: float = Field(default=0.0, ge=0.0, description="Cost of a million prompt tokens (decrease user budget)")
    cost_completion_tokens: float = Field(default=0.0, ge=0.0, description="Cost of a million completion tokens (decrease user budget)")


class UpdateRouter(BaseModel):
    name: constr(strip_whitespace=True, min_length=1) | None = Field(default=None, description="Name of the model router.", examples=["model-router-1"])  # fmt: off
    type: ModelType | None = Field(default=None, description="Type of the model router. It will be used to identify the model router type.", examples=["text-generation"])  # fmt: off
    aliases: list[constr(strip_whitespace=True, min_length=1, max_length=64)] | None = Field(default=None, description="Aliases of the model. It will be used to identify the model by users.", examples=[["model-alias", "model-alias-2"]])  # fmt: off
    load_balancing_strategy: RouterLoadBalancingStrategy | None = Field(default=None, description="Routing strategy for load balancing between providers of the model. It will be used to identify the model type.", examples=["least_busy"])  # fmt: off
    cost_prompt_tokens: float | None = Field(default=None, ge=0.0, description="Cost of a million prompt tokens (decrease user budget)")
    cost_completion_tokens: float | None = Field(default=None, ge=0.0, description="Cost of a million completion tokens (decrease user budget)")


class Router(BaseModel):
    object: Literal["router"] = "router"
    id: int = Field(..., description="ID of the router.")  # fmt: off
    name: str = Field(..., description="Name of the router.")  # fmt: off
    user_id: int = Field(..., description="ID of the user that owns the router.")  # fmt: off
    type: ModelType = Field(..., description="Type of the model router. It will be used to identify the model router type.", examples=["text-generation"])  # fmt: off
    aliases: list[str] | None = Field(default=None, description="Aliases of the model. It will be used to identify the model by users.", examples=[["model-alias", "model-alias-2"]])  # fmt: off
    load_balancing_strategy: RouterLoadBalancingStrategy = Field(..., description="Routing strategy for load balancing between providers of the model. It will be used to identify the model type.", examples=["least_busy"])  # fmt: off
    vector_size: int | None = Field(default=None, description="Dimension of the vectors, if the models are embeddings. Make sure it is the same for all models.")  # fmt: off
    max_context_length: int | None = Field(default=None, description="Maximum amount of tokens a context could contains. Make sure it is the same for all models.")  # fmt: off
    cost_prompt_tokens: float = Field(description="Cost of a million prompt tokens (decrease user budget)")
    cost_completion_tokens: float = Field(description="Cost of a million completion tokens (decrease user budget)")
    providers: int = Field(default=0, description="Number of providers in the router.")  # fmt: off
    created: int = Field(..., description="Time of creation, as Unix timestamp.")  # fmt: off
    updated: int = Field(..., description="Time of last update, as Unix timestamp.")  # fmt: off


class Routers(BaseModel):
    object: Literal["list"] = "list"
    data: list[Router]
