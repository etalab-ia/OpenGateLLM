from enum import Enum
from typing import Any

from fastapi import UploadFile
from pydantic import BaseModel

from api.schemas.parse import ParsedDocumentOutputFormat


class ParserParams(BaseModel):
    file: UploadFile
    output_format: ParsedDocumentOutputFormat | None = None
    force_ocr: bool | None = None
    page_range: str = ""
    paginate_output: bool | None = None
    use_llm: bool | None = None


class FileType(str, Enum):
    PDF = "pdf"
    HTML = "html"
    JSON = "json"
    MD = "md"
    TXT = "txt"


class JsonFileDocument(BaseModel):
    title: str | None = None
    text: str
    metadata: dict[str, Any] = {}


class JsonFile(BaseModel):
    documents: list[JsonFileDocument]
