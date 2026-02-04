from enum import Enum
from typing import Any

from pydantic import BaseModel


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
