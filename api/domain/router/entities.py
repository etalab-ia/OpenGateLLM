from enum import Enum

from pydantic import BaseModel, Field


class ModelCosts(BaseModel):
    prompt_tokens: float = Field(default=0.0, ge=0.0, description="Cost of a million prompt tokens (decrease user budget)")
    completion_tokens: float = Field(default=0.0, ge=0.0, description="Cost of a million completion tokens (decrease user budget)")


class ModelType(str, Enum):
    AUTOMATIC_SPEECH_RECOGNITION = "automatic-speech-recognition"
    IMAGE_TEXT_TO_TEXT = "image-text-to-text"
    IMAGE_TO_TEXT = "image-to-text"
    TEXT_EMBEDDINGS_INFERENCE = "text-embeddings-inference"
    TEXT_GENERATION = "text-generation"
    TEXT_CLASSIFICATION = "text-classification"


class Model(BaseModel):
    id: str = Field(..., description="The model identifier, which can be referenced in the API endpoints.")
    type: ModelType = Field(..., description="The type of the model, which can be used to identify the model type.", examples=["text-generation"])  # fmt: off
    aliases: list[str] | None = Field(default=None, description="Aliases of the model. It will be used to identify the model by users.", examples=[["model-alias", "model-alias-2"]])  # fmt: off
    created: int = Field(..., description="Time of creation, as Unix timestamp.")
    owned_by: str = Field(..., description="The organization that owns the model.")
    max_context_length: int | None = Field(default=None, description="Maximum amount of tokens a context could contains. Makes sure it is the same for all models.")  # fmt: off
    costs: ModelCosts = Field(..., description="Costs of the model.")


class RouterLoadBalancingStrategy(str, Enum):
    SHUFFLE = "shuffle"
    LEAST_BUSY = "least_busy"


class Router(BaseModel):
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
