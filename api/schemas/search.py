from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from api.schemas import BaseModel
from api.schemas.chunks import Chunk
from api.schemas.usage import Usage
from api.utils.exceptions import WrongSearchMethodException


class SearchMethod(StrEnum):
    HYBRID = "hybrid"
    SEMANTIC = "semantic"
    LEXICAL = "lexical"


class SearchArgs(BaseModel):
    collection_ids: Annotated[list[int], Field(min_length=1, max_length=100, alias="collections", description="List of collections ID")]
    limit: Annotated[int, Field(gt=0, le=100, default=10, description="Number of results to return")]
    offset: Annotated[int, Field(ge=0, default=0, description="Offset for pagination, specifying how many results to skip from the beginning")]
    method: Annotated[SearchMethod, Field(default=SearchMethod.SEMANTIC, description="Search method to use")]
    rff_k: Annotated[int, Field(default=60, ge=0, le=16384, description="Smoothing constant for Reciprocal Rank Fusion (RRF) algorithm in hybrid search (recommended: from 10 to 100).")]  # fmt: off
    score_threshold: Annotated[float, Field(default=0.0, ge=0.0, le=1.0, description="Score of cosine similarity threshold for filtering results, only available for semantic search method.")]  # fmt: off

    @model_validator(mode="after")
    def validate_score_threshold(self) -> "SearchArgs":
        if self.score_threshold > 0.0 and self.method != SearchMethod.SEMANTIC:
            raise WrongSearchMethodException(detail="Score threshold is only available for semantic search method.")

        return self


class SearchRequest(SearchArgs):
    prompt: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(description="Prompt related to the search")]


class Search(BaseModel):
    method: Annotated[SearchMethod, Field(description="Search method used.")]
    score: Annotated[float, Field(description="Score of the search result.")]
    chunk: Annotated[Chunk, Field(description="Chunk of the search result.")]


class Searches(BaseModel):
    object: Annotated[Literal["list"], Field(default="list", description="The type of the object.")]
    data: Annotated[list[Search], Field(description="List of search results.")]
    usage: Annotated[Usage, Field(default_factory=Usage, description="Usage information for the request.")]
