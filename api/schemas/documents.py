from datetime import datetime
from enum import Enum
import json
from typing import Literal

from fastapi import File, Form, UploadFile
from fastapi.exceptions import RequestValidationError
from langchain_text_splitters import Language
from pydantic import ConfigDict, Field, ValidationError, conint, conlist, constr, field_serializer, field_validator, model_validator

from api.schemas import BaseModel
from api.utils.exceptions import FileSizeLimitExceededException

PresetSeparators = Enum("PresetSeparators", {**{m.name: m.value for m in Language}, **{"EMPTY": ""}}, type=str)


class Document(BaseModel):
    object: Literal["document"] = "document"
    id: int
    name: str
    collection_id: int
    created: int
    chunks: int | None = None


class Documents(BaseModel):
    object: Literal["list"] = "list"
    data: list[Document]


class DocumentResponse(BaseModel):
    id: int = Field(default=..., description="The ID of the document created.")


class Chunker(str, Enum):
    RECURSIVE_CHARACTER_TEXT_SPLITTER = "RecursiveCharacterTextSplitter"
    NO_SPLITTER = "NoSplitter"


class InputChunkMetadata(BaseModel):
    source_ref: constr(strip_whitespace=True, min_length=1, max_length=255) | None = Field(default=None, description="The reference to the source of the document. Use it to locate the chunk in the source document (ex: doc-1#page-1#section-1). If not provided, no reference will be stored.")  # fmt: off
    source_url: constr(strip_whitespace=True, min_length=1, max_length=255) | None = Field(default=None, description="The URL of the source of the document. Use it to display the source document in the UI. If not provided, no URL will be stored.")  # fmt: off
    source_type: constr(strip_whitespace=True, min_length=1, max_length=255) | None = Field(default=None, description="The type of the source of the document. Use it to display the source document in the UI. If not provided, no type will be stored.")  # fmt: off
    source_page: conint(ge=0, le=9999) | None = Field(default=None, description="The page number of the source of the document. Use it to display the source document in the UI. If not provided, no page number will be stored.")  # fmt: off
    source_format: constr(strip_whitespace=True, min_length=1, max_length=255) | None = Field(default=None, description="The format of the source of the document. If not provided, format will be inferred from the file type (`pdf`, `html`, `md` or `txt`).")  # fmt: off
    source_title: constr(strip_whitespace=True, min_length=1, max_length=255) | None = Field(default=None, description="The title of the source of the document. Use it to display the source document in the UI. If not provided, no title will be stored.")  # fmt: off
    source_format: constr(strip_whitespace=True, min_length=1, max_length=255) | None = Field(default=None, description="The format of the source of the document. If not provided, format will be inferred from the file type (`pdf`, `html`, `md` or `txt`).")  # fmt: off
    source_author: constr(strip_whitespace=True, min_length=1, max_length=255) | None = Field(default=None, description="The author of the source of the document. If not provided, no author will be stored.")  # fmt: off
    source_publisher: constr(strip_whitespace=True, min_length=1, max_length=255) | None = Field(default=None, description="The publisher of the source of the document. If not provided, no publisher will be stored.")  # fmt: off
    source_priority: conint(ge=1, le=10) = Field(default=1, description="The priority of the source of the document.")  # fmt: off
    source_tags: conlist(item_type=constr(strip_whitespace=True, min_length=1, max_length=255), min_length=0, max_length=10) = Field(default=[], description="The tags of the source of the document. Use it to categorize the source document. If not provided, no tags will be stored.")  # fmt: off
    source_date: datetime | None = Field(default=None, description="The date of the source of the document. Use it to date the source document. If not provided, no date will be stored.")  # fmt: off

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def parse_metadata(cls, data: object) -> object:
        if data is None:
            return {}
        if isinstance(data, str):
            data = data.strip()
            data = "{}" if data == "" else data
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                raise ValueError("metadata must be a JSON object")
        return data

    @field_validator("source_tags")
    def remove_duplicates_source_tags(cls, source_tags: list[str]) -> list[str]:
        return list(set(source_tags))

    @field_serializer("source_date")
    def serialize_source_date(self, source_date: datetime | None) -> int | None:
        if source_date is None:
            return None
        return int(source_date.timestamp())


class CreateDocumentForm(BaseModel):
    file: UploadFile
    chunker: Chunker
    chunk_min_size: int
    chunk_overlap: int
    chunk_size: int
    collection: int
    is_separator_regex: bool
    separators: list[str]
    preset_separators: PresetSeparators
    metadata: InputChunkMetadata

    @field_validator("file")
    def validate_file(cls, file: UploadFile) -> UploadFile:
        if file.size > FileSizeLimitExceededException.MAX_CONTENT_SIZE:
            raise FileSizeLimitExceededException()
        return file

    @model_validator(mode="after")
    def validate_separators(self) -> "CreateDocumentForm":
        if self.preset_separators == PresetSeparators.EMPTY:
            self.preset_separators = None

        if self.preset_separators == PresetSeparators.EMPTY and self.separators == []:
            raise ValueError("separators and preset_separators cannot by empty at the same time")

        return self

    # fmt: off
    @classmethod
    def as_form(
        cls,
        file: UploadFile = File(default=..., description="The file to create a document from."),
        collection: int = Form(default=..., description="The collection ID to use for the file upload. The file will be vectorized with model defined by the collection."),
        chunker: Chunker = Form(default=Chunker.RECURSIVE_CHARACTER_TEXT_SPLITTER, description="The name of the chunker to use for the file upload."),
        chunk_min_size: int = Form(default=0, description="The minimum size in characters of the chunks to use for the file upload."),
        chunk_overlap: int = Form(default=0, description="The overlap in characters of the chunks to use for the file upload."),
        chunk_size: int = Form(default=2048, description="The size in characters of the chunks to use for the file upload."),
        is_separator_regex: bool = Form(default=False, description="Whether the separator is a regex to use for the file upload."),
        separators: list[str] = Form(default=[], description="The separators to use for the file upload."),
        preset_separators: PresetSeparators = Form(default=PresetSeparators.MARKDOWN, description="If provided, override separators by the preset specific separators. See [implemented details](https://github.com/langchain-ai/langchain/blob/eb122945832eae9b9df7c70ccd8d51fcd7a1899b/libs/text-splitters/langchain_text_splitters/character.py#L164). If not provided, the language will be inferred from the file type."),
        metadata: InputChunkMetadata = Form(default=InputChunkMetadata(), description="Additional metadata to add to each chunk. Provide a stringified JSON object matching the Metadata schema.", examples=['{"source_title": "Example title", "source_tags": ["tag-1", "tag-2"]}']),
    ) -> "CreateDocumentForm":
        try:
            return cls(
                file=file,
                chunker=chunker,
                chunk_min_size=chunk_min_size,
                chunk_overlap=chunk_overlap,
                chunk_size=chunk_size,
                collection=collection,
                is_separator_regex=is_separator_regex,
                separators=separators,
                preset_separators=preset_separators,
                metadata=metadata,
            )
        except ValidationError as exc:
            raise RequestValidationError(exc.errors())
