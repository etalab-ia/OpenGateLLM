from enum import Enum
from typing import Literal

from fastapi import File, UploadFile
from langchain_text_splitters import Language
from pydantic import Field, field_validator

from api.schemas import BaseModel


class Chunker(str, Enum):
    RECURSIVE_CHARACTER_TEXT_SPLITTER = "RecursiveCharacterTextSplitter"
    NO_SPLITTER = "NoSplitter"


class CreateDocumentForm(BaseModel):
    file: UploadFile = File(default=..., description="The file to create a document from.")  # fmt: off
    force_ocr: bool = Field(default=False, description="Force OCR on all pages of the PDF.  Defaults to False.  This can lead to worse results if you have good text in your PDFs (which is true in most cases).")  # fmt: off
    chunker: Chunker = Field(default=Chunker.RECURSIVE_CHARACTER_TEXT_SPLITTER, description="The name of the chunker to use for the file upload.")  # fmt: off
    chunk_min_size: int = Field(default=0, description="The minimum size of the chunks to use for the file upload.")  # fmt: off
    chunk_overlap: int = Field(default=0, description="The overlap of the chunks to use for the file upload.")  # fmt: off
    chunk_size: int = Field(default=2048, description="The size of the chunks to use for the file upload.")  # fmt: off
    collection: int = Field(default=..., description="The collection ID to use for the file upload. The file will be vectorized with model defined by the collection.")  # fmt: off
    is_separator_regex: bool = Field(default=False, description="Whether the separator is a regex to use for the file upload.")  # fmt: off
    separators: list[str] = Field(default=["\n\n", "\n", ". ", " "], description="The separators to use for the file upload.")  # fmt: off
    preset_separators: Language = Field(default="", description="If provided, override separators by the preset specific separators. See [implemented details](https://github.com/langchain-ai/langchain/blob/eb122945832eae9b9df7c70ccd8d51fcd7a1899b/libs/text-splitters/langchain_text_splitters/character.py#L164).")  # fmt: off
    metadata: dict[str, str | int | float | bool] = Field(default={}, description="Additional metadata to add to each chunk. Only a flattened JSON is allowed with string, int, float, or bool values. Example: {\"string_metadata\": \"test\", \"int_metadata\": 1, \"float_metadata\": 1.0, \"bool_metadata\": true}")  # fmt: off

    @field_validator("preset_separators")
    def validate_preset_separators(cls, preset_separators: Language) -> str:
        if preset_separators == Language.EMPTY:
            return None
        return preset_separators


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
