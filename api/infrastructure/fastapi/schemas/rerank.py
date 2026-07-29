from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from api.domain import BaseModel
from api.domain.usage.entities import Usage


class CreateRerankBody(BaseModel):
    query: Annotated[str, StringConstraints(min_length=1, strip_whitespace=True), Field(description="The search query to use for the reranking. `query` and `prompt` cannot both be provided.")]  # fmt: off
    documents: list[Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)], Field(description="A list of texts that will be compared to the query and ranked by relevance. `documents` and `input` cannot both be provided.")]  # fmt: off
    model: Annotated[str, StringConstraints(min_length=1, strip_whitespace=True), Field(default=..., description="The model to use for the reranking, call `/v1/models` endpoint to get the list of available models, only `text-classification` model type is supported.")]  # fmt: off
    top_n: Annotated[int | None, Field(default=None, ge=1, description="The number of top results to return. If set to None, all results will be returned.")]  # fmt: off


class RerankResult(BaseModel):
    relevance_score: Annotated[float, Field(description="The relevance score of the reranked text.")]
    index: Annotated[int, Field(description="The index of the reranked text.")]


class RerankResponse(BaseModel):
    object: Annotated[Literal["list"], Field(default="list", description="Type of object.")]
    id: Annotated[str, Field(default=..., description="A unique identifier for the request.")]
    results: Annotated[list[RerankResult], Field(default=..., description="The list of reranked texts.")]
    model: Annotated[str, Field(default=..., description="The model used to generate the reranking.")]
    usage: Annotated[Usage, Field(default_factory=Usage, description="Usage information for the request.")]
