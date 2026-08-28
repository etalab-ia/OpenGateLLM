from datetime import UTC, datetime, timedelta
from enum import StrEnum
import logging
from typing import Annotated, Literal

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
import httpx
from jose import jwt
from pydantic import (
    ConfigDict,
    Field,
    GetJsonSchemaHandler,
    PositiveInt,
    StringConstraints,
    TypeAdapter,
    ValidationError,
    field_serializer,
    field_validator,
    model_validator,
)
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.key.entities import Key
from api.schemas import BaseModel
from api.schemas.core.models import RequestContent
from api.schemas.usage import Usage
from api.sql.models import Token as KeyTable
from api.utils.exceptions import WrongSearchMethodException

from ._identityaccessmanager import IdentityAccessManager

logger = logging.getLogger(__name__)


MIN_NUMBER, MAX_NUMBER = -9999999999999999, 9999999999999999

MetadataStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
MetadataInt = Annotated[int, Field(ge=MIN_NUMBER, le=MAX_NUMBER)]
MetadataFloat = Annotated[float, Field(ge=MIN_NUMBER, le=MAX_NUMBER)]
ChunkMetadata = Annotated[dict[MetadataStr, MetadataStr | MetadataInt | MetadataFloat | bool], Field(description="Extra metadata for the source", min_length=1, max_length=10)]  # fmt: off


class InputChunk(BaseModel):
    content: Annotated[str, Field(default=..., description="The content of the chunk.")]
    metadata: Annotated[ChunkMetadata | None, Field(default=None, description="Metadata of the chunk")]


class Chunk(BaseModel):
    object: Annotated[Literal["chunk"], Field(default="chunk", description="The type of the object.")]
    id: Annotated[int, Field(ge=0, default=..., description="The ID of the chunk.")]
    collection_id: Annotated[int, Field(ge=0, default=..., description="The ID of the collection the chunk belongs to.")]
    document_id: Annotated[int, Field(ge=0, default=..., description="The ID of the document the chunk belongs to.")]
    content: Annotated[str, Field(min_length=1, default=..., description="The content of the chunk.")]
    metadata: Annotated[ChunkMetadata | None, Field(default=None, description="Metadata of the chunk")]
    created: Annotated[datetime, Field(default_factory=lambda: datetime.now(tz=UTC), description="The date of the chunk creation.")]

    @field_validator("metadata", mode="before")
    @classmethod
    def support_legacy_metadata(cls, metadata: dict | None) -> dict | None:
        if metadata is None:
            return None

        normalized_metadata = {}
        for key, value in metadata.items():
            if value is None:
                continue
            if isinstance(value, list):
                normalized_value = ",".join(str(item).strip() for item in value if str(item).strip())
                if normalized_value:
                    normalized_metadata[key] = normalized_value
                continue
            normalized_metadata[key] = value

        return normalized_metadata

    @field_serializer("created")
    def serialize_created(self, created: datetime) -> int:
        return int(created.timestamp())


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
    collection_ids: Annotated[list[PositiveInt], Field(default=[], min_length=0, max_length=100, description="List of collections ID.")]  # fmt: off
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
    query: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(..., description="Query related to the search.")]  # fmt: off
    model_config = ConfigDict(populate_by_name=True)


class Search(BaseModel):
    method: Annotated[SearchMethod, Field(description="Search method used.")]
    score: Annotated[float, Field(description="Score of the search result.")]
    chunk: Annotated[Chunk, Field(description="Chunk of the search result.")]


class Searches(BaseModel):
    object: Annotated[Literal["list"], Field(default="list", description="The type of the object.")]
    data: Annotated[list[Search], Field(description="List of search results.")]
    usage: Annotated[Usage, Field(default_factory=Usage, description="Usage information for the request.")]


class SearchTool:
    PROMPT_TEMPLATE = """
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

    SYSTEM_KEY_NAME = "_system_search_tool"

    def __init__(self, opengaterag_url: str, postgres_session: AsyncSession, user_id: int, secret_key: str):
        self.opengaterag_url = opengaterag_url
        self.postgres_session = postgres_session
        self.user_id = user_id
        self.secret_key = secret_key

    async def call(self, request_content: RequestContent) -> RequestContent:
        tools = request_content.body.get("tools", [])
        if tools is None:
            return request_content

        search_args = None

        for i, tool in enumerate(tools):
            if tool.get("type") == "search":
                search_tool = request_content.body["tools"].pop(i)
                search_tool.pop("type")
                try:
                    search_args = SearchArgs(**search_tool)
                    metadata_filters = TypeAdapter(ComparisonFilter | CompoundFilter | None).validate_python(search_tool.get("metadata_filters"))
                    search_args.metadata_filters = metadata_filters
                except ValidationError as e:
                    raise HTTPException(status_code=422, detail=jsonable_encoder(e.errors()))
                break

        if not search_args:
            return request_content

        request_content.additional_data["search_results"] = []

        messages = request_content.body.get("messages", [])
        if not messages:
            return request_content
        query = messages[-1].get("content")
        if not query:
            return request_content

        expire_time = datetime.now(UTC) + timedelta(hours=1)
        key = await self._upsert_key(user_id=self.user_id, name=self.SYSTEM_KEY_NAME, expire=expire_time)

        if key is None:
            return request_content

        results = []
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url=f"{self.opengaterag_url}/v1/search",
                    headers={"Authorization": f"Bearer {key.value}"},
                    json={"query": query, **search_args.model_dump()},
                    timeout=60,
                )
        except Exception as e:
            return request_content
        try:
            response.raise_for_status()
        except Exception:
            try:
                detail = response.json()["detail"]
            except Exception:
                detail = response.text
            raise HTTPException(status_code=response.status_code, detail=detail)

        results = response.json()

        if len(results["data"]) > 0:
            chunks = "\n".join([result["chunk"]["content"] for result in results["data"]])
            request_content.body["messages"][-1]["content"] = SearchTool.PROMPT_TEMPLATE.format(query=query, chunks=chunks)

        request_content.additional_data["search_results"] = results["data"]

        return request_content

    def _encode_token(self, user_id: int, token_id: int, expires: datetime | None = None) -> str:
        expires = int(expires.timestamp()) if expires is not None else None
        return IdentityAccessManager.TOKEN_PREFIX + jwt.encode(
            claims={"user_id": user_id, "token_id": token_id, "expires": expires},
            key=self.secret_key,
            algorithm="HS256",
        )

    async def _upsert_key(self, user_id: int, name: str, expire: datetime) -> Key | None:
        try:
            result = await self.postgres_session.execute(
                pg_insert(KeyTable)
                .values(user_id=user_id, name=name, expires=expire)
                .on_conflict_do_update(constraint="unique_token_name_per_user", set_={"expires": expire})
                .returning(KeyTable)
            )
            row = result.scalar_one()

        except IntegrityError as e:
            if "token_user_id_fkey" in str(e.orig):
                return None
            raise

        value = self._encode_token(user_id=user_id, token_id=row.id, expires=expire)
        registered_value = f"{value[:8]}...{value[-8:]}"
        await self.postgres_session.execute(update(KeyTable).values(token=registered_value).where(KeyTable.id == row.id))
        await self.postgres_session.commit()

        return Key(id=row.id, name=row.name, user_id=row.user_id, value=value, expires=row.expires, created=row.created)
