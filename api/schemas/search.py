from enum import Enum
from typing import Literal

from pydantic import Field, constr, model_validator

from api.schemas import BaseModel
from api.schemas.chunks import Chunk
from api.schemas.usage import Usage
from api.utils.exceptions import WrongSearchMethodException


class SearchMethod(str, Enum):
    """Enum representing the search methods available (will be displayed in this order in playground)."""

    HYBRID = "hybrid"
    SEMANTIC = "semantic"
    LEXICAL = "lexical"


class SearchArgs(BaseModel):
    collections: list[int] = Field(min_length=1, max_length=100, description="List of collections ID")
    rff_k: int = Field(
        default=60,
        ge=0,
        le=16384,
        description="Smoothing constant for Reciprocal Rank Fusion (RRF) algorithm in hybrid search (recommended: from 10 to 100).",
    )
    k: int = Field(gt=0, le=200, default=10, deprecated=True, description="[DEPRECATED: use limit instead]Number of results to return")
    limit: int = Field(gt=0, le=200, default=10, description="Number of results to return")
    offset: int = Field(ge=0, default=0, description="Offset for pagination, specifying how many results to skip from the beginning")
    method: SearchMethod = Field(default=SearchMethod.SEMANTIC)
    score_threshold: float | None = Field(default=0.0, ge=0.0, le=1.0, description="Score of cosine similarity threshold for filtering results, only available for semantic search method.")  # fmt: off

    @model_validator(mode="after")
    def score_threshold_filter(cls, values):
        if values.score_threshold and values.method not in SearchMethod.SEMANTIC:
            raise WrongSearchMethodException(detail="Score threshold is only available for semantic search method.")
        return values

    @model_validator(mode="before")
    def handle_deprecated_fields(cls, data):
        if isinstance(data, dict):
            if "k" in data and "limit" not in data:
                data["limit"] = data["k"]
        return data


class SearchRequest(SearchArgs):
    prompt: constr(strip_whitespace=True, min_length=1) = Field(description="Prompt related to the search")


class Search(BaseModel):
    method: SearchMethod
    score: float
    chunk: Chunk


class Searches(BaseModel):
    object: Literal["list"] = "list"
    data: list[Search]
    usage: Usage = Field(default_factory=Usage, description="Usage information for the request.")
