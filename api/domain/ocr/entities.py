from typing import Any, Literal

from pydantic import Field

from api.domain import BaseModel
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


class CreateOCRBody(BaseModel):
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
        # OCR requests carry no textual prompt: rate limiting and cost are based on 0 prompt tokens.
        return []


class OCRUsage(BaseModel):
    doc_size_bytes: int | None = Field(default=None, description="Document size in bytes")
    pages_processed: int = Field(default=..., description="Number of pages processed")


class OCRPageDimensions(BaseModel):
    dpi: int = Field(default=..., description="Dots per inch of the page-image")
    height: int = Field(default=..., description="Height of the image in pixels")
    width: int = Field(default=..., description="Width of the image in pixels")


class OCRImageObject(BaseModel):
    bottom_right_x: int | None = Field(default=None, description="X coordinate of bottom-right corner of the extracted image")
    bottom_right_y: int | None = Field(default=None, description="Y coordinate of bottom-right corner of the extracted image")
    id: str = Field(default=..., description="Image ID for extracted image in a page")
    image_annotation: str | None = Field(default=None, description="Annotation of the extracted image in json str")
    image_base64: str | None = Field(default=None, description="Base64 string of the extracted image")
    top_left_x: int | None = Field(default=None, description="X coordinate of top-left corner of the extracted image")
    top_left_y: int | None = Field(default=None, description="Y coordinate of top-left corner of the extracted image")


class OCRPageObject(BaseModel):
    dimensions: OCRPageDimensions | None = Field(default=None, description="The dimensions of the PDF Page's screenshot image")
    images: list[OCRImageObject] = Field(default=..., description="List of all extracted images in the page.")
    index: int = Field(default=..., description="The page index in a pdf document starting from 0")
    markdown: str | None = Field(default=None, description="The markdown string response of the page")


class OCR(BaseModel):
    document_annotation: str | None = Field(default=None, description="Formatted response in the request_format if provided in json str")
    id: str | None = Field(default=None, description="The ID of the OCR request.")
    model: str | None = Field(default=None, description="The model used to generate the OCR.")
    pages: list[OCRPageObject] = Field(default=..., description="List of OCR info for pages.")
    usage: Usage | None = Field(default=None, description="Usage information for the request.")
    usage_info: OCRUsage | None = Field(default=None, description="Usage information for the request.")
