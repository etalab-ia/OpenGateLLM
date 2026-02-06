from enum import Enum
import json
from typing import Annotated, Literal

from fastapi import File, Form, UploadFile
from fastapi.exceptions import RequestValidationError
from langchain_text_splitters import Language
from pydantic import Field, StringConstraints, TypeAdapter, ValidationError, field_validator, model_validator

from api.schemas import BaseModel
from api.schemas.chunks import ChunkMetadata
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


class CreateDocumentForm(BaseModel):
    file: UploadFile
    chunker: Chunker
    chunk_min_size: int
    chunk_overlap: Annotated[int, Field(ge=0)]
    chunk_size: Annotated[int, Field(ge=0)]
    collection: int
    is_separator_regex: bool
    separators: list[str]
    preset_separators: PresetSeparators
    metadata: str

    @field_validator("file")
    @classmethod
    def validate_file(cls, file: UploadFile) -> UploadFile:
        if file.size > FileSizeLimitExceededException.MAX_CONTENT_SIZE:
            raise FileSizeLimitExceededException()
        return file

    @field_validator("metadata", mode="after")
    @classmethod
    def parse_metadata(cls, metadata: str) -> dict | None:
        if metadata == "":
            return None
        try:
            metadata = json.loads(metadata)
            return TypeAdapter(ChunkMetadata).validate_python(metadata)
        except json.JSONDecodeError:
            raise ValueError("metadata must be a JSON object")
        except ValidationError as e:
            raise e

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
        separators: list[str] = Form(default=[], description="The separators to use for the file upload. `separators` and `preset_separators`parameters cannot by empty at the same time."),
        preset_separators: PresetSeparators = Form(default=PresetSeparators.MARKDOWN, description="If provided, override separators by the preset specific separators. See [implemented details](https://github.com/langchain-ai/langchain/blob/eb122945832eae9b9df7c70ccd8d51fcd7a1899b/libs/text-splitters/langchain_text_splitters/character.py#L164). `separators` and `preset_separators`parameters cannot by empty at the same time."),
        metadata: Annotated[str, StringConstraints(strip_whitespace=True)] = Form(default="", description="Optional additional metadata to add to each chunk. Provide a stringified JSON object matching the Metadata schema.", examples=['{"source_date": "2026-01-05", "source_tags": ["tag1", "tag2"]}']),
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
