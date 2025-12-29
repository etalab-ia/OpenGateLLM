from typing import Literal

from pydantic import Field

from api.schemas import BaseModel
from api.schemas.usage import Usage


class RerankRequest(BaseModel):
    prompt: str | None = Field(default=None, description="The prompt to use for the reranking.", deprecated=True)  # fmt: off
    query: str | None = Field(default=None, description="The search query to use for the reranking.")  # fmt: off
    input: list[str] | None = Field(default=None, description="List of input texts to rerank by relevance to the prompt.", deprecated=True)  # fmt: off
    documents: list[str] | None = Field(default=None, description="A list of texts that will be compared to the query and ranked by relevance.")  # fmt: off
    model: str = Field(default=..., description="The model to use for the reranking, call `/v1/models` endpoint to get the list of available models, only `text-classification` model type is supported.")  # fmt: off
    top_n: int = Field(default=5, description="The number of top results to return.")


class Rerank(BaseModel):
    object: Literal["rerank"] = "rerank"
    score: float
    index: int


class Reranks(BaseModel):
    id: str = Field(default=None, description="A unique identifier for the reranking.")
    object: Literal["list"] = "list"
    data: list[Rerank]
    usage: Usage = Field(default_factory=Usage, description="Usage information for the request.")
