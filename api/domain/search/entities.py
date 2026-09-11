from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, ClassVar, Literal

from pydantic import ConfigDict, Field, PositiveInt, StringConstraints, model_validator

from api.domain import BaseModel, UtcDatetime

MIN_NUMBER, MAX_NUMBER = -9999999999999999, 9999999999999999

MetadataStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
MetadataInt = Annotated[int, Field(ge=MIN_NUMBER, le=MAX_NUMBER)]
MetadataFloat = Annotated[float, Field(ge=MIN_NUMBER, le=MAX_NUMBER)]
ChunkMetadata = Annotated[dict[MetadataStr, MetadataStr | MetadataInt | MetadataFloat | bool], Field(min_length=1, max_length=10)]


class SearchMethod(StrEnum):
    HYBRID = "hybrid"
    SEMANTIC = "semantic"
    LEXICAL = "lexical"


class ComparisonFilterType(StrEnum):
    EQ = "eq"
    SW = "sw"
    EW = "ew"
    CO = "co"


class CompoundFilterOperator(StrEnum):
    AND = "and"
    OR = "or"


class ComparisonFilter(BaseModel):
    key: MetadataStr
    type: ComparisonFilterType
    value: MetadataStr | MetadataInt | MetadataFloat | bool


class CompoundFilter(BaseModel):
    filters: Annotated[list[ComparisonFilter], Field(min_length=2, max_length=4)]
    operator: CompoundFilterOperator


class SearchArgs(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    collection_ids: Annotated[list[PositiveInt], Field(default=[], min_length=0, max_length=100)]
    document_ids: Annotated[list[PositiveInt], Field(default=[], min_length=0, max_length=100)]
    metadata_filters: ComparisonFilter | CompoundFilter | None = None
    limit: Annotated[int, Field(gt=0, le=100, default=10)]
    offset: Annotated[int, Field(ge=0, default=0)]
    method: SearchMethod = SearchMethod.SEMANTIC
    rff_k: Annotated[int, Field(default=60, ge=0, le=16384)]
    score_threshold: Annotated[float, Field(default=0.0, ge=0.0, le=1.0)]

    @model_validator(mode="after")
    def validate_score_threshold(self) -> "SearchArgs":
        if self.score_threshold > 0.0 and self.method != SearchMethod.SEMANTIC:
            raise ValueError("Score threshold is only available for semantic search method.")

        return self


class Chunk(BaseModel):
    object: Literal["chunk"] = "chunk"
    id: Annotated[int, Field(ge=0)]
    collection_id: Annotated[int, Field(ge=0)]
    document_id: Annotated[int, Field(ge=0)]
    content: Annotated[str, Field(min_length=1)]
    metadata: ChunkMetadata | None = None
    created: Annotated[UtcDatetime, Field(default_factory=lambda: datetime.now(tz=UTC))]


class Search(BaseModel):
    method: SearchMethod
    score: float
    chunk: Chunk


class Searches(BaseModel):
    PROMPT_TEMPLATE: ClassVar[str] = """
Respond to the user's query using only information found in the provided retrieved documents.
- Detect the language of the user's query  and reply in that language.
- Make factual claims only if supported by the retrieved documents. If the answer is not present, clearly state: "I do not know based on the provided documents." in the same language as the user's query.
- If no documents are retrieved, state: "No documents were provided; this answer does not rely on documents." in the same language as the user's query.
- Keep your response concise and clear.

Context:
- User query: {query}
- Retrieved documents:
{chunks}

Output Format:
- Reply in the user's language.
- Attribute each fact to its source by document position (e.g., "According to Document 1: ...").
- If no documents are provided, state: "No documents were provided; this answer does not rely on documents."
- If none of the documents answer the query, state: "I do not know based on the provided documents."
"""

    object: Literal["list"] = "list"
    data: list[Search] = []

    def build_grounded_prompt(self, query: str) -> str:
        chunks = "\n".join(search.chunk.content for search in self.data)

        return self.PROMPT_TEMPLATE.format(query=query, chunks=chunks)
