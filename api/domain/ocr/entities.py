from typing import Annotated, Literal

from pydantic import Field

from api.domain import BaseModel, ForwardablePayload
from api.domain.model.entities import ProviderJsonResponse
from api.domain.usage.entities import Usage


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
    document: OCRDocumentURLChunk | OCRImageURLChunk
    document_annotation_prompt: str | None = None
    model: str

    def get_prompts(self) -> list[str]:
        return [self.document_annotation_prompt] if self.document_annotation_prompt else []


class OCRUsage(BaseModel):
    doc_size_bytes: int | None = None
    pages_processed: int


class OCRPageDimensions(BaseModel):
    dpi: int
    height: int
    width: int


class OCRImageObject(BaseModel):
    bottom_right_x: int | None = None
    bottom_right_y: int | None = None
    id: str
    image_annotation: str | None = None
    image_base64: str | None = None
    top_left_x: int | None = None
    top_left_y: int | None = None


class OCRPageObject(BaseModel):
    dimensions: OCRPageDimensions | None = None
    images: list[OCRImageObject]
    index: int
    markdown: str | None = None


class OCR(ProviderJsonResponse):
    id: str
    model: str
    document_annotation: str | None = None
    pages: list[OCRPageObject]
    usage: Annotated[Usage, Field(default_factory=Usage)]
    usage_info: OCRUsage | None = None

    def get_completions(self) -> list[str]:
        texts = [page.markdown for page in self.pages if page.markdown]
        if self.document_annotation:
            texts.append(self.document_annotation)
        return texts
