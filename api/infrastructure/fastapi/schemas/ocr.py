from typing import Annotated, Any, Literal

from pydantic import Field, StringConstraints

from api.domain import BaseModel
from api.domain.usage.entities import Usage


class JsonSchema(BaseModel):
    name: Annotated[str, Field(default=..., description="The name of the JSON schema.")]
    schema: Annotated[dict[str, Any], Field(default=..., description="The JSON schema definition.")]
    strict: Annotated[bool, Field(default=False, description="Whether to use strict mode.")]
    description: Annotated[str | None, Field(default=None, description="Optional description of the schema.")]


class ResponseFormat(BaseModel):
    type: Annotated[Literal["text", "json_object", "json_schema"], Field(default="text", description='Specify the format that the model must output. By default it will use `{ "type": "text" }`. Setting to `{ "type": "json_object" }` enables JSON mode, which guarantees the message the model generates is in JSON. When using JSON mode you MUST also instruct the model to produce JSON yourself with a system or a user message. Setting to `{ "type": "json_schema" }` enables JSON schema mode, which guarantees the message the model generates is in JSON and follows the schema you provide.')]  # fmt: off
    json_schema: Annotated[JsonSchema | None, Field(default=None, description="The JSON schema definition. Required when type is 'json_schema'.")]  # fmt: off


class DocumentURLChunk(BaseModel):
    document_name: Annotated[str | None, Field(default=None, description="The filename of the document.")]
    document_url: Annotated[str, Field(default=..., description="The URL of the document.")]
    type: Annotated[Literal["document_url"], Field(default="document_url", description="The type of the document.")]


class ImageURL(BaseModel):
    detail: Annotated[str | None, Field(default=None, description="The detail of the image.")]
    url: Annotated[str, Field(default=..., description="The URL of the image.")]


class ImageURLChunk(BaseModel):
    image_url: Annotated[ImageURL | str, Field(default=..., description="The URL of the image to OCR.")]
    type: Annotated[Literal["image_url"], Field(default="image_url", description="The type of the image.")]


class CreateOCRBody(BaseModel):
    bbox_annotation_format: Annotated[ResponseFormat | None, Field(default=None, description='Specify the format that the model must output for the bounding boxes. By default it will use `{ "type": "text" }`. Setting to `{ "type": "json_object" }` enables JSON mode, which guarantees the message the model generates is in JSON. When using JSON mode you MUST also instruct the model to produce JSON yourself with a system or a user message. Setting to `{ "type": "json_schema" }` enables JSON schema mode, which guarantees the message the model generates is in JSON and follows the schema you provide.')]  # fmt: off
    document: Annotated[DocumentURLChunk | ImageURLChunk, Field(default=..., description="Document to run OCR on.")]
    document_annotation_format: Annotated[ResponseFormat | None, Field(default=None, description='Specify the format that the model must output for the document. By default it will use `{ "type": "text" }`. Setting to `{ "type": "json_object" }` enables JSON mode, which guarantees the message the model generates is in JSON. When using JSON mode you MUST also instruct the model to produce JSON yourself with a system or a user message. Setting to `{ "type": "json_schema" }` enables JSON schema mode, which guarantees the message the model generates is in JSON and follows the schema you provide.')]  # fmt: off
    document_annotation_prompt: Annotated[str | None, Field(default=None, description="Optional prompt to guide the model in extracting structured output from the entire document. A document_annotation_format must be provided.")]  # fmt: off
    extract_footer: Annotated[bool, Field(default=False, description="Whether to extract the footer of the document.")]
    extract_header: Annotated[bool, Field(default=False, description="Whether to extract the header of the document.")]
    image_limit: Annotated[int | None, Field(default=None, description="Max images to extract")]
    image_min_size: Annotated[int | None, Field(default=None, description="Minimum height and width of image to extract")]
    include_image_base64: Annotated[bool | None, Field(default=None, description="Include image URLs in response")]
    model: Annotated[str | None, StringConstraints(strip_whitespace=True), Field(default=None, description="The model to use for the OCR, call `/v1/models` endpoint to get the list of available models, only `image-to-text` model type is supported.")]  # fmt: off
    pages: Annotated[list[int] | None, Field(default=None, description="Specific pages to process. Accepts a list of integers or a string of comma-separated numbers and ranges (e.g. '0,1,2' or '0-5' or '0,2-4'). Page numbers start from 0.")]  # fmt: off
    table_format: Annotated[Literal["markdown", "html"] | None, Field(default=None, description="Format for table extraction: 'markdown' (default) or 'html'.")]  # fmt: off


class OCRUsage(BaseModel):
    doc_size_bytes: Annotated[int | None, Field(default=None, description="Document size in bytes")]
    pages_processed: Annotated[int, Field(default=..., description="Number of pages processed")]


class OCRPageDimensions(BaseModel):
    dpi: Annotated[int, Field(default=..., description="Dots per inch of the page-image")]
    height: Annotated[int, Field(default=..., description="Height of the image in pixels")]
    width: Annotated[int, Field(default=..., description="Width of the image in pixels")]


class OCRImageObject(BaseModel):
    bottom_right_x: Annotated[int | None, Field(default=None, description="X coordinate of bottom-right corner of the extracted image")]
    bottom_right_y: Annotated[int | None, Field(default=None, description="Y coordinate of bottom-right corner of the extracted image")]
    id: Annotated[str, Field(default=..., description="Image ID for extracted image in a page")]
    image_annotation: Annotated[str | None, Field(default=None, description="Annotation of the extracted image in json str")]
    image_base64: Annotated[str | None, Field(default=None, description="Base64 string of the extracted image")]
    top_left_x: Annotated[int | None, Field(default=None, description="X coordinate of top-left corner of the extracted image")]
    top_left_y: Annotated[int | None, Field(default=None, description="Y coordinate of top-left corner of the extracted image")]


class OCRPageObject(BaseModel):
    dimensions: Annotated[OCRPageDimensions | None, Field(default=None, description="The dimensions of the PDF Page's screenshot image")]
    images: Annotated[list[OCRImageObject], Field(default=..., description="List of all extracted images in the page.")]
    index: Annotated[int, Field(default=..., description="The page index in a pdf document starting from 0")]
    markdown: Annotated[str | None, Field(default=None, description="The markdown string response of the page")]


class OCRResponse(BaseModel):
    document_annotation: Annotated[str | None, Field(default=None, description="Formatted response in the request_format if provided in json str")]  # fmt: off
    id: Annotated[str | None, Field(default=None, description="The ID of the OCR request.")]
    model: Annotated[str | None, Field(default=None, description="The model used to generate the OCR.")]
    pages: Annotated[list[OCRPageObject], Field(default=..., description="List of OCR info for pages.")]
    usage: Annotated[Usage | None, Field(default=None, description="Usage information for the request.")]
    usage_info: Annotated[OCRUsage | None, Field(default=None, description="Usage information for the request.")]
