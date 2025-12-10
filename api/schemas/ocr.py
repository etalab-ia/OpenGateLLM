from typing import Any, Literal

from fastapi import Form
from pydantic import Field

from api.schemas import BaseModel
from api.schemas.usage import Usage

DEFAULT_PROMPT = """Tu es un système d'OCR très précis. Extrait tout le texte visible de cette image. 
Ne décris pas l'image, n'ajoute pas de commentaires. Réponds uniquement avec le texte brut extrait, 
en préservant les paragraphes, la mise en forme et la structure du document. 
Si aucun texte n'est visible, réponds avec 'Aucun texte détecté'. 
Je veux une sortie au format markdown. Tu dois respecter le format de sortie pour bien conserver les tableaux."""


ModelForm: str = Form(default=..., description="The model to use for the OCR.")  # fmt: off
DPIForm: int = Form(default=150, ge=100, le=600, description="The DPI to use for the OCR (each page will be rendered as an image at this DPI).")  # fmt: off
PromptForm: str = Form(default=DEFAULT_PROMPT, description="The prompt to use for the OCR.")  # fmt: off


class JsonSchema(BaseModel):
    name: str = Field(..., description="The name of the JSON schema.")
    schema_definition: dict[str, Any] = Field(..., description="The JSON schema definition.")
    strict: bool = Field(default=False, description="Whether to use strict mode.")
    description: str | None = Field(default=None, description="Optional description of the schema.")


class ResponseFormat(BaseModel):
    type: Literal["text", "json_object", "json_schema"] = Field(default="text", description='Specify the format that the model must output. By default it will use `{ "type": "text" }`. Setting to `{ "type": "json_object" }` enables JSON mode, which guarantees the message the model generates is in JSON. When using JSON mode you MUST also instruct the model to produce JSON yourself with a system or a user message. Setting to `{ "type": "json_schema" }` enables JSON schema mode, which guarantees the message the model generates is in JSON and follows the schema you provide.')  # fmt: off
    json_schema: JsonSchema | None = Field(default=None, description="The JSON schema definition. Required when type is 'json_schema'.")  # fmt: off


class FileChunk(BaseModel):
    file_id: str = Field(default=..., description="The ID of the file.", )  # fmt: off
    type: Literal["file"] = Field(default="file", description="The type of the file.")  # fmt: off


class DocumentURLChunk(BaseModel):
    document_name: str | None = Field(default=None, description="The filename of the document.")  # fmt: off
    document_url: str = Field(default=..., description="The URL of the document.")  # fmt: off
    type: Literal["document_url"] = Field(default="document_url", description="The type of the document.")  # fmt: off


class ImageURL(BaseModel):
    detail: str | None = Field(default=None, description="The detail of the image.")  # fmt: off
    url: str = Field(default=..., description="The URL of the image.")  # fmt: off


class ImageURLChunk(BaseModel):
    image_url: ImageURL | str = Field(default=..., description="The URL of the image to OCR.")  # fmt: off
    type: Literal["image_url"] = Field(default="image_url", description="The type of the image.")  # fmt: off


class CreateOCR(BaseModel):
    bbox_annotation_format: ResponseFormat | None = Field(default=None, description='Specify the format that the model must output for the bounding boxes. By default it will use `{ "type": "text" }`. Setting to `{ "type": "json_object" }` enables JSON mode, which guarantees the message the model generates is in JSON. When using JSON mode you MUST also instruct the model to produce JSON yourself with a system or a user message. Setting to `{ "type": "json_schema" }` enables JSON schema mode, which guarantees the message the model generates is in JSON and follows the schema you provide.')  # fmt: off
    document: DocumentURLChunk | ImageURLChunk = Field(default=..., description="Document to run OCR on.")  # fmt: off
    document_annotation_format: ResponseFormat | None = Field(default=None, description='Specify the format that the model must output for the document. By default it will use `{ "type": "text" }`. Setting to `{ "type": "json_object" }` enables JSON mode, which guarantees the message the model generates is in JSON. When using JSON mode you MUST also instruct the model to produce JSON yourself with a system or a user message. Setting to `{ "type": "json_schema" }` enables JSON schema mode, which guarantees the message the model generates is in JSON and follows the schema you provide.')  # fmt: off
    # id: str = Field(default=..., description="The ID of the OCR.")  # fmt: off
    image_limit: int | None = Field(default=None, description="Max images to extract")  # fmt: off
    image_min_size: int | None = Field(default=None, description="Minimum height and width of image to extract")  # fmt: off
    include_image_base64: bool | None = Field(default=None, description="Include image URLs in response")  # fmt: off
    model: str | None = Field(default=None, description="The model to use for the OCR.")  # fmt: off
    pages: list[int] | None = Field(default=None, description="Specific pages user wants to process in various formats: single number, range, or list of both. Starts from 0")  # fmt: off


class OCRUsage(BaseModel):
    doc_size_bytes: int | None = Field(default=None, description="Document size in bytes")  # fmt: off
    pages_processed: int = Field(default=..., description="Number of pages processed")  # fmt: off


class OCRPageDimensions(BaseModel):
    dpi: int = Field(default=..., description="Dots per inch of the page-image")  # fmt: off
    height: int = Field(default=..., description="Height of the image in pixels")  # fmt: off
    width: int = Field(default=..., description="Width of the image in pixels")  # fmt: off


class OCRImageObject(BaseModel):
    bottom_right_x: int | None = Field(default=None, description="X coordinate of bottom-right corner of the extracted image")  # fmt: off
    bottom_right_y: int | None = Field(default=None, description="Y coordinate of bottom-right corner of the extracted image")  # fmt: off
    id: str = Field(default=..., description="Image ID for extracted image in a page")  # fmt: off
    image_annotation: str | None = Field(default=None, description="Annotation of the extracted image in json str")  # fmt: off
    image_base64: str | None = Field(default=None, description="Base64 string of the extracted image")  # fmt: off
    top_left_x: int | None = Field(default=None, description="X coordinate of top-left corner of the extracted image")  # fmt: off
    top_left_y: int | None = Field(default=None, description="Y coordinate of top-left corner of the extracted image")  # fmt: off


class OCRPageObject(BaseModel):
    dimensions: OCRPageDimensions | None = Field(default=None, description="The dimensions of the PDF Page's screenshot image")  # fmt: off
    images: list[OCRImageObject] = Field(default=..., description="List of all extracted images in the page.")  # fmt: off
    index: int = Field(default=..., description="The page index in a pdf document starting from 0")  # fmt: off
    markdown: str | None = Field(default=None, description="The markdown string response of the page")  # fmt: off


class OCR(BaseModel):
    document_annotation: str | None = Field(default=None, description="Formatted response in the request_format if provided in json str")  # fmt: off
    id: str | None = Field(default=None, description="The ID of the OCR request.")  # fmt: off
    model: str | None = Field(default=None, description="The model used to generate the OCR.")  # fmt: off
    pages: list[OCRPageObject] = Field(default=..., description="List of OCR info for pages.")  # fmt: off
    usage: Usage | None = Field(default=None, description="Usage information for the request.")  # fmt: off
    usage_info: OCRUsage | None = Field(default=None, description="Usage information for the request.")  # fmt: off
