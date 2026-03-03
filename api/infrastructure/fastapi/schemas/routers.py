from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from api.schemas import BaseModel
from api.schemas.models import ModelType


class RouterLoadBalancingStrategy(StrEnum):
    SHUFFLE = "shuffle"
    LEAST_BUSY = "least_busy"


class CreateRouterBody(BaseModel):
    name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1), Field(..., description="Name of the model router.", examples=["model-router-1"])
    ]
    router_type: Annotated[
        ModelType,
        Field(
            ...,
            description="Type of the model router. It will be used to identify the model router type.",
            examples=["text-generation"],
            alias="type",
        ),
    ]
    aliases: Annotated[
        list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]],
        Field(
            default_factory=list,
            description="Aliases of the model. It will be used to identify the model by users.",
            examples=[["model-alias", "model-alias-2"]],
        ),
    ]
    load_balancing_strategy: Annotated[
        RouterLoadBalancingStrategy,
        Field(
            default=RouterLoadBalancingStrategy.SHUFFLE,
            description="Routing strategy for load balancing between providers of the model. It will be used to identify the model type.",
        ),
    ]
    cost_prompt_tokens: Annotated[float, Field(default=0.0, ge=0.0, description="Cost of a million prompt tokens (decrease user budget)")]
    cost_completion_tokens: Annotated[float, Field(default=0.0, ge=0.0, description="Cost of a million completion tokens (decrease user budget)")]


class UpdateRouterBody(BaseModel):
    name: Annotated[
        str | None,
        StringConstraints(strip_whitespace=True, min_length=1),
        Field(default=None, description="Name of the model router.", examples=["model-router-1"]),
    ]
    router_type: Annotated[
        ModelType | None,
        Field(
            default=None,
            description="Type of the model router. It will be used to identify the model router type.",
            examples=["text-generation"],
            alias="type",
        ),
    ]
    aliases: Annotated[
        list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]] | None,
        Field(
            default=None,
            description="Aliases of the model. It will be used to identify the model by users.",
            examples=[["model-alias", "model-alias-2"]],
        ),
    ]
    load_balancing_strategy: Annotated[
        RouterLoadBalancingStrategy | None,
        Field(
            default=None,
            description="Routing strategy for load balancing between providers of the model. It will be used to identify the model type.",
            examples=["least_busy"],
        ),
    ]
    cost_prompt_tokens: Annotated[float | None, Field(default=None, ge=0.0, description="Cost of a million prompt tokens (decrease user budget)")]
    cost_completion_tokens: Annotated[
        float | None, Field(default=None, ge=0.0, description="Cost of a million completion tokens (decrease user budget)")
    ]


class RouterResponse(BaseModel):
    object: Annotated[Literal["router"], Field("router", description="Type of the object.")]
    id: Annotated[int, Field(..., description="ID of the router.")]
    name: Annotated[str, Field(..., description="Name of the router.")]
    user_id: Annotated[int, Field(..., description="ID of the user that owns the router.")]
    router_type: Annotated[
        ModelType,
        Field(
            ...,
            description="Type of the model router. It will be used to identify the model router type.",
            alias="type",
            examples=["text-generation"],
        ),
    ]
    aliases: Annotated[
        list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]],
        Field(
            default=...,
            description="Aliases of the model. It will be used to identify the model by users.",
            examples=[["model-alias", "model-alias-2"]],
        ),
    ]
    load_balancing_strategy: Annotated[
        RouterLoadBalancingStrategy,
        Field(
            ...,
            description="Routing strategy for load balancing between providers of the model. It will be used to identify the model type.",
            examples=["least_busy"],
        ),
    ]
    vector_size: Annotated[
        int | None,
        Field(default=None, description="Dimension of the vectors, if the models are embeddings. Make sure it is the same for all models."),
    ]
    max_context_length: Annotated[
        int | None, Field(default=None, description="Maximum amount of tokens a context could contains. Make sure it is the same for all models.")
    ]
    cost_prompt_tokens: Annotated[float, Field(description="Cost of a million prompt tokens (decrease user budget)")]
    cost_completion_tokens: Annotated[float, Field(description="Cost of a million completion tokens (decrease user budget)")]
    providers: Annotated[int, Field(default=0, description="Number of providers in the router.")]
    created: Annotated[int, Field(..., description="Time of creation, as Unix timestamp.")]
    updated: Annotated[int, Field(..., description="Time of last update, as Unix timestamp.")]


class Routers(BaseModel):
    object: Annotated[Literal["list"], Field("list", description="Type of the object.")]
    total: Annotated[int, Field(..., description="Total number of routers.")]
    offset: Annotated[int, Field(..., description="Offset of the routers list.")]
    limit: Annotated[int, Field(..., description="Limit of the routers list.")]
    data: Annotated[list[RouterResponse], Field(..., description="List of routers.")]
