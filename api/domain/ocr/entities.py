from typing import Any, Literal

from pydantic import Field

from api.domain import BaseModel, ForwardablePayload
from api.domain.model.entities import ModelJsonResponse
from api.domain.usage.entities import Usage


class OCRJsonSchema(BaseModel):
    name: str
    schema: dict[str, Any]
    strict: bool = False
    description: str | None = None


class OCRResponseFormat(BaseModel):
    type: Literal["text", "json_object", "json_schema"] = "text"
    json_schema: OCRJsonSchema | None = None


class OCRDocumentURLChunk(BaseModel):
    document_name: str | None = None
    document_url: str
    type: Literal["document_url"] = "document_url"


class OCRImageURL(BaseModel):
    detail: str | None = None
    url: str


class OCRImageURLChunk(BaseModel):
    image_url: OCRImageURL | str
    type: Literal["image_url"] = "image_url"


class CreateOCRBody(ForwardablePayload):
    bbox_annotation_format: OCRResponseFormat | None = None
    document: OCRDocumentURLChunk | OCRImageURLChunk
    document_annotation_format: OCRResponseFormat | None = None
    document_annotation_prompt: str | None = None
    extract_footer: bool = False
    extract_header: bool = False
    image_limit: int | None = None
    image_min_size: int | None = None
    include_image_base64: bool | None = None
    model: str | None = None
    pages: list[int] | None = None
    table_format: Literal["markdown", "html"] | None = None

    def get_prompts(self) -> list[str]:
        return [self.document_annotation_prompt] if self.document_annotation_prompt else []


class OCRUsage(BaseModel):
    doc_size_bytes: int | None
    pages_processed: int


class OCRPageDimensions(BaseModel):
    dpi: int
    height: int
    width: int


class OCRImageObject(BaseModel):
    bottom_right_x: int | None
    bottom_right_y: int | None
    id: str
    image_annotation: str | None
    image_base64: str | None
    top_left_x: int | None
    top_left_y: int | None


class OCRPageObject(BaseModel):
    dimensions: OCRPageDimensions | None
    images: list[OCRImageObject]
    index: int
    markdown: str | None


class OCR(ModelJsonResponse):
    id: str
    model: str
    document_annotation: str | None
    pages: list[OCRPageObject]
    usage: Usage = Field(default_factory=Usage)
    usage_info: OCRUsage | None

    def get_completions(self) -> list[str]:
        texts = [page.markdown for page in self.pages if page.markdown]
        if self.document_annotation:
            texts.append(self.document_annotation)
        return texts
