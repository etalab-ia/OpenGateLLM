from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AliasChoices, ConfigDict, Field, GetJsonSchemaHandler, PositiveInt, StringConstraints, model_validator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema

from api.schemas import BaseModel
from api.schemas.chunks import Chunk, MetadataFloat, MetadataInt, MetadataStr
from api.schemas.usage import Usage
from api.utils.exceptions import WrongSearchMethodException


class SearchMethod(StrEnum):
    HYBRID = "hybrid"
    SEMANTIC = "semantic"
    LEXICAL = "lexical"


class ComparisonFilterType(StrEnum):
    EQ = "eq"
    SW = "sw"
    EW = "ew"
    CO = "co"

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        schema = handler(core_schema)
        schema["description"] = "Comparison filter type for metadata filters."
        schema["x-enumDescriptions"] = {
            "eq": "Equal to the value provided.",
            "sw": "Starts with the value provided.",
            "ew": "Ends with the value provided.",
            "co": "Contains the value provided.",
        }
        return schema


class CompoundFilterOperator(StrEnum):
    AND = "and"
    OR = "or"

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        schema = handler(core_schema)
        schema["description"] = "Compound filter operator for metadata filters."
        schema["x-enumDescriptions"] = {"and": "AND operator", "or": "OR operator"}
        return schema


class ComparisonFilter(BaseModel):
    key: MetadataStr
    type: ComparisonFilterType
    value: MetadataStr | MetadataInt | MetadataFloat | bool


class CompoundFilter(BaseModel):
    filters: Annotated[list[ComparisonFilter], Field(min_length=2, max_length=4, description="List of filters to apply to the search.")]
    operator: Annotated[CompoundFilterOperator, Field(description="Operator to use for the compound filter.")]


class SearchArgs(BaseModel):
    collection_ids: Annotated[list[PositiveInt], Field(default=[], min_length=0, max_length=100, validation_alias=AliasChoices("collection_ids", "collections"), serialization_alias="collection_ids", description="List of collections ID.")]  # fmt: off
    document_ids: Annotated[list[PositiveInt], Field(default=[], min_length=0, max_length=100, description="List of document IDs")]
    metadata_filters: Annotated[ComparisonFilter | CompoundFilter | None, Field(default=None, description="Metadata filters to apply to the search.")]  # fmt: off
    limit: Annotated[int, Field(gt=0, le=100, default=10, description="Number of results to return.")]
    offset: Annotated[int, Field(ge=0, default=0, description="Offset for pagination, specifying how many results to skip from the beginning.")]
    method: Annotated[SearchMethod, Field(default=SearchMethod.SEMANTIC, description="Search method to use.")]
    rff_k: Annotated[int, Field(default=60, ge=0, le=16384, description="Smoothing constant for Reciprocal Rank Fusion (RRF) algorithm in hybrid search (recommended: from 10 to 100).")]  # fmt: off
    score_threshold: Annotated[float, Field(default=0.0, ge=0.0, le=1.0, description="Score of cosine similarity threshold for filtering results, only available for semantic search method.")]  # fmt: off

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def validate_score_threshold(self) -> "SearchArgs":
        if self.score_threshold > 0.0 and self.method != SearchMethod.SEMANTIC:
            raise WrongSearchMethodException(detail="Score threshold is only available for semantic search method")

        return self


class CreateSearch(SearchArgs):
    query: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1), Field(default=None, validation_alias=AliasChoices("query", "prompt"), serialization_alias="query", description="Query related to the search.")]  # fmt: off
    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def validate_query(self) -> "CreateSearch":
        if not self.query:
            if not self.prompt:
                raise ValueError("query or prompt must be provided")
            else:
                self.query = self.prompt

        return self


class Search(BaseModel):
    method: Annotated[SearchMethod, Field(description="Search method used.")]
    score: Annotated[float, Field(description="Score of the search result.")]
    chunk: Annotated[Chunk, Field(description="Chunk of the search result.")]


class Searches(BaseModel):
    object: Annotated[Literal["list"], Field(default="list", description="The type of the object.")]
    data: Annotated[list[Search], Field(description="List of search results.")]
    usage: Annotated[Usage, Field(default_factory=Usage, description="Usage information for the request.")]
