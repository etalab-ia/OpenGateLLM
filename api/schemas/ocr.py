from typing import Any, Literal

from mistralai.client.models import OCRResponse
from pydantic import Field

from api.schemas import BaseModel
from api.schemas.usage import Usage


class JsonSchema(BaseModel):
    name: str = Field(..., description="The name of the JSON schema.")
    schema: dict[str, Any] = Field(..., description="The JSON schema definition.")
    strict: bool = Field(default=False, description="Whether to use strict mode.")
    description: str | None = Field(default=None, description="Optional description of the schema.")


class ResponseFormat(BaseModel):
    type: Literal["text", "json_object", "json_schema"] = Field(default="text", description='Specify the format that the model must output. By default it will use `{ "type": "text" }`. Setting to `{ "type": "json_object" }` enables JSON mode, which guarantees the message the model generates is in JSON. When using JSON mode you MUST also instruct the model to produce JSON yourself with a system or a user message. Setting to `{ "type": "json_schema" }` enables JSON schema mode, which guarantees the message the model generates is in JSON and follows the schema you provide.')  # fmt: off
    json_schema: JsonSchema | None = Field(default=None, description="The JSON schema definition. Required when type is 'json_schema'.")  # fmt: off


class FileChunk(BaseModel):
    file_id: str = Field(default=..., description="The ID of the file.")
    type: Literal["file"] = Field(default="file", description="The type of the file.")


class DocumentURLChunk(BaseModel):
    document_name: str | None = Field(default=None, description="The filename of the document.")
    document_url: str = Field(default=..., description="The URL of the document.")
    type: Literal["document_url"] = Field(default="document_url", description="The type of the document.")


class ImageURL(BaseModel):
    detail: str | None = Field(default=None, description="The detail of the image.")
    url: str = Field(default=..., description="The URL of the image.")


class ImageURLChunk(BaseModel):
    image_url: ImageURL | str = Field(default=..., description="The URL of the image to OCR.")
    type: Literal["image_url"] = Field(default="image_url", description="The type of the image.")


class CreateOCR(BaseModel):
    bbox_annotation_format: ResponseFormat | None = Field(default=None, description='Specify the format that the model must output for the bounding boxes. By default it will use `{ "type": "text" }`. Setting to `{ "type": "json_object" }` enables JSON mode, which guarantees the message the model generates is in JSON. When using JSON mode you MUST also instruct the model to produce JSON yourself with a system or a user message. Setting to `{ "type": "json_schema" }` enables JSON schema mode, which guarantees the message the model generates is in JSON and follows the schema you provide.')  # fmt: off
    # confidence_scores_granularity: Literal["word", "page"] | None = Field(default=None, description="Granularity for confidence scores: 'word' (per-word scores) or 'page' (aggregate only). Defaults to None (no confidence scores) to keep response payload small.")  # fmt: off
    document: DocumentURLChunk | ImageURLChunk = Field(default=..., description="Document to run OCR on.")
    document_annotation_format: ResponseFormat | None = Field(default=None, description='Specify the format that the model must output for the document. By default it will use `{ "type": "text" }`. Setting to `{ "type": "json_object" }` enables JSON mode, which guarantees the message the model generates is in JSON. When using JSON mode you MUST also instruct the model to produce JSON yourself with a system or a user message. Setting to `{ "type": "json_schema" }` enables JSON schema mode, which guarantees the message the model generates is in JSON and follows the schema you provide.')  # fmt: off
    document_annotation_prompt: str | None = Field(default=None, description="Optional prompt to guide the model in extracting structured output from the entire document. A document_annotation_format must be provided.")  # fmt: off
    extract_footer: bool = Field(default=False, description="Whether to extract the footer of the document.")
    extract_header: bool = Field(default=False, description="Whether to extract the header of the document.")
    image_limit: int | None = Field(default=None, description="Max images to extract")
    image_min_size: int | None = Field(default=None, description="Minimum height and width of image to extract")
    # include_blocks: bool = Field(default=False, description="Return paragraph-level bounding boxes for all content blocks in the response.")
    include_image_base64: bool | None = Field(default=None, description="Include image URLs in response")
    model: str | None = Field(default=None, description="The model to use for the OCR.")
    pages: list[int] | None = Field(default=None, description="Specific pages to process. Accepts a list of integers or a string of comma-separated numbers and ranges (e.g. '0,1,2' or '0-5' or '0,2-4'). Page numbers start from 0.")  # fmt: off
    table_format: Literal["markdown", "html"] | None = Field(default="markdown", description="Format for table extraction: 'markdown' (default) or 'html'.")  # fmt: off


class OCR(OCRResponse):
    usage: Usage | None = Field(default=None, description="Usage information for the request.")
