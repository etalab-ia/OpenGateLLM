from enum import StrEnum
import json
from typing import Annotated, Literal

from fastapi import File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from langchain_text_splitters import Language
from pydantic import Field, StringConstraints, TypeAdapter, ValidationError, field_validator, model_validator

from api.schemas import BaseModel
from api.schemas.chunks import ChunkMetadata
from api.utils.exceptions import FileSizeLimitExceededException

PresetSeparators = StrEnum("PresetSeparators", {**{m.name: m.value for m in Language}})


class Document(BaseModel):
    object: Annotated[Literal["document"], Field(default="document", description="The type of the object.")]
    id: Annotated[int, Field(gt=0, default=..., description="The ID of the document.")]
    name: Annotated[str, Field(min_length=1, default=..., description="The name of the document.")]
    collection_id: Annotated[int, Field(gt=0, default=..., description="The ID of the collection the document belongs to.")]
    created: Annotated[int, Field(default=..., description="The date of the document creation.")]
    chunks: Annotated[int, Field(ge=0, default=0, description="The number of chunks the document has.")]


class Documents(BaseModel):
    object: Annotated[Literal["list"], Field(default="list", description="The type of the object.")]
    data: Annotated[list[Document], Field(min_length=0, description="List of documents.")]


class CreateDocumentForm(BaseModel):
    file: UploadFile | None
    name: Annotated[str | None, StringConstraints(min_length=1, max_length=255, strip_whitespace=True)] | None
    collection_id: int
    disable_chunking: bool
    chunk_size: int
    chunk_min_size: int
    chunk_overlap: int
    is_separator_regex: bool
    separators: list[str]
    preset_separators: PresetSeparators
    metadata: str

    @field_validator("file")
    @classmethod
    def validate_file(cls, file: UploadFile | None) -> UploadFile | None:
        if file is None:
            return file
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
    def validate_form(self) -> "CreateDocumentForm":
        if self.file is None and self.name is None:
            raise ValueError("name is required when file is not provided")

        return self

    # fmt: off
    @classmethod
    async def as_form(
        cls,
        request: Request,
        file: UploadFile | None = File(default=None, description="The file to create a document from. If not provided, the document will be created without content, use POST `/v1/documents/{document_id}/chunks` to fill it."),
        name: str | None = Form(default=None, description="Name of document if no file is provided or to override file name."),
        collection_id: int | None = Form(gt=0, default=None, description="The collection ID to use for the file upload. The file will be vectorized with model defined by the collection."),
        collection: int | None = Form(gt=0, default=None, include_in_schema=False, deprecated=True),
        disable_chunking: bool = Form(default=False, description="Whether to disable `RecursiveCharacterTextSplitter` chunking for the upload file."),
        chunk_size: int = Form(ge=0, default=2048, description="The size in characters of the chunks to use for the upload file. If not provided, the document will not be split into chunks."),
        chunk_min_size: int = Form(ge=0, default=0, description="The minimum size in characters of the chunks to use for the upload file."),
        chunk_overlap: int = Form(ge=0, default=0, description="The overlap in characters of the chunks to use for the upload file."),
        is_separator_regex: bool = Form(default=False, description="Whether the separator is a regex to use for the upload file."),
        separators: list[str] = Form(min_length=0, default=[], description="Delimiters used by RecursiveCharacterTextSplitter for further splitting. If provided, `preset_separators` is ignored."),
        preset_separators: PresetSeparators = Form(default=PresetSeparators.MARKDOWN, description="Preset separators used by RecursiveCharacterTextSplitter for further splitting. See [implemented details](https://github.com/langchain-ai/langchain/blob/eb122945832eae9b9df7c70ccd8d51fcd7a1899b/libs/text-splitters/langchain_text_splitters/character.py#L164)."),
        metadata: str = Form(default="", description="Optional additional metadata to add to each chunk if a file is provided. Provide a stringified JSON object matching the Metadata schema.", examples=['{"source_date": "2026-01-05", "source_tags": ["tag1", "tag2"]}']),
    ) -> "CreateDocumentForm":
        collection_id = collection_id if collection_id is not None else collection
        try:
            return cls(
                file=file,
                name=name,
                collection_id=collection_id,
                disable_chunking=disable_chunking,
                chunk_min_size=chunk_min_size,
                chunk_overlap=chunk_overlap,
                chunk_size=chunk_size,
                is_separator_regex=is_separator_regex,
                separators=separators,
                preset_separators=preset_separators,
                metadata=metadata,
            )
        except ValidationError as exc:
            raise RequestValidationError(exc.errors())


class DocumentResponse(BaseModel):
    id: Annotated[int, Field(ge=0, default=..., description="The ID of the document created.")]
