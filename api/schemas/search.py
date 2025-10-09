from enum import Enum
from typing import Any, List, Literal, Optional

from pydantic import Field, constr, model_validator

from api.schemas import BaseModel
from api.schemas.chunks import Chunk
from api.schemas.usage import Usage
from api.utils.exceptions import WrongSearchMethodException


class SearchMethod(str, Enum):
    """Enum representing the search methods available (will be displayed in this order in playground)."""

    MULTIAGENT = "multiagent"
    HYBRID = "hybrid"
    SEMANTIC = "semantic"
    LEXICAL = "lexical"


class SearchArgs(BaseModel):
    collections: List[Any] = Field(default=[], description="List of collections ID")
    rff_k: int = Field(default=20, description="k constant in RFF algorithm")
    k: int = Field(gt=0, le=200, default=10, deprecated=True, description="[DEPRECATED: use limit instead]Number of results to return")
    limit: int = Field(gt=0, le=200, default=10, description="Number of results to return")
    offset: int = Field(gt=0, default=0, description="Offset for pagination, specifying how many results to skip from the beginning")
    method: SearchMethod = Field(default=SearchMethod.SEMANTIC)
    score_threshold: Optional[float] = Field(default=0.0, ge=0.0, le=1.0, description="Score of cosine similarity threshold for filtering results, only available for semantic search method.")  # fmt: off
    web_search: bool = Field(default=False, description="Whether add internet search to the results.")
    web_search_k: int = Field(default=5, description="Number of results to return for web search.")

    @model_validator(mode="after")
    def score_threshold_filter(cls, values):
        if values.score_threshold and values.method not in (SearchMethod.SEMANTIC, SearchMethod.MULTIAGENT):
            raise WrongSearchMethodException(detail="Score threshold is only available for semantic and multiagent search methods.")
        return values

    @model_validator(mode="before")
    def handle_deprecated_fields(cls, data):
        if isinstance(data, dict):
            if 'k' in data and 'limit' not in data:
                data['limit'] = data['k']
        return data


class SearchRequest(SearchArgs):
    prompt: constr(strip_whitespace=True, min_length=1) = Field(description="Prompt related to the search")


class Search(BaseModel):
    method: SearchMethod
    score: float
    chunk: Chunk


class Searches(BaseModel):
    object: Literal["list"] = "list"
    data: List[Search]
    usage: Usage = Field(default_factory=Usage, description="Usage information for the request.")
