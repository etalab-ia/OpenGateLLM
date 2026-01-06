import re
from typing import Any, Literal

from fastapi import Form
from pydantic import Field, constr, model_validator

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
    document_name: constr(strip_whitespace=True, min_length=1) | None = Field(default=None, description="The filename of the document.")  # fmt: off
    document_url: constr(pattern=r"^http[s]?://|data:application/pdf;base64,", strip_whitespace=True, min_length=1) = Field(default=..., description="The URL of the document.")  # fmt: off
    type: Literal["document_url"] = Field(default="document_url", description="The type of the document.")  # fmt: off


class ImageURL(BaseModel):
    detail: str | None = Field(default=None, description="The detail of the image.")  # fmt: off
    url: constr(pattern=r"^http[s]?://|data:image/[^;]+;base64,", strip_whitespace=True, min_length=1) = Field(default=..., description="The URL of the image.")  # fmt: off


class ImageURLChunk(BaseModel):
    image_url: ImageURL | str = Field(default=..., description="The URL of the image to OCR.")  # fmt: off
    type: Literal["image_url"] = Field(default="image_url", description="The type of the image.")  # fmt: off


class CreateOCR(BaseModel):
    bbox_annotation_format: ResponseFormat | None = Field(default=None, description='Specify the format that the model must output for the bounding boxes. By default it will use `{ "type": "text" }`. Setting to `{ "type": "json_object" }` enables JSON mode, which guarantees the message the model generates is in JSON. When using JSON mode you MUST also instruct the model to produce JSON yourself with a system or a user message. Setting to `{ "type": "json_schema" }` enables JSON schema mode, which guarantees the message the model generates is in JSON and follows the schema you provide.')  # fmt: off
    document: DocumentURLChunk | ImageURLChunk = Field(default=..., description="Document to run OCR on.")  # fmt: off
    document_annotation_format: ResponseFormat | None = Field(default=None, description='Specify the format that the model must output for the document. By default it will use `{ "type": "text" }`. Setting to `{ "type": "json_object" }` enables JSON mode, which guarantees the message the model generates is in JSON. When using JSON mode you MUST also instruct the model to produce JSON yourself with a system or a user message. Setting to `{ "type": "json_schema" }` enables JSON schema mode, which guarantees the message the model generates is in JSON and follows the schema you provide.')  # fmt: off
    # id: str = Field(default=..., description="The ID of the OCR.")  # fmt: off # TODO: add this
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


class MarkerCreateOCR(CreateOCR):
    page_range: str = Field(default="", description="Page range to convert, specify comma separated page numbers or ranges. Example: '0,5-10,20'")  # fmt: off
    force_ocr: bool = Field(default=False, description="Force OCR on all pages of the PDF.  Defaults to False.  This can lead to worse results if you have good text in your PDFs (which is true in most cases).")  # fmt: off
    paginate_output: bool = Field(default=False, description="Whether to paginate the output.  Defaults to False.  If set to True, each page of the output will be separated by a horizontal rule that contains the page number (2 newlines, {PAGE_NUMBER}, 48 - characters, 2 newlines).")  # fmt: off
    output_format: Literal["markdown", "json", "html"] = Field(default="markdown", description="The format to output the text in.  Can be 'markdown', 'json', or 'html'.  Defaults to 'markdown'.")  # fmt: off

    class ConfigDict:
        extra = "allow"

    @staticmethod
    def pages_to_page_range(pages: list[int] | None) -> str:
        if not pages:
            return ""

        pages = sorted(pages)
        ranges = []
        start = prev = pages[0]
        for p in pages[1:]:
            if p == prev + 1:
                prev = p
            else:
                ranges.append(f"{start}-{prev}" if start != prev else str(start))
                start = prev = p
        ranges.append(f"{start}-{prev}" if start != prev else str(start))

        return ",".join(ranges)

    @model_validator(mode="after")
    def validate_model(self):
        self.page_range = self.pages_to_page_range(self.pages)
        if self.document_annotation_format is not None:
            match self.document_annotation_format.type:
                case "text":
                    self.output_format = "markdown"
                case "json_object":
                    self.output_format = "json"
                case "json_schema":
                    raise ValueError("json_schema format is not supported for Marker models")
        else:
            self.output_format = "markdown"

        if self.bbox_annotation_format is not None:
            raise ValueError("bbox_annotation_format parameter is not supported for Marker models")

        if self.document_annotation_format is not None:
            raise ValueError("document_annotation_format parameter is not supported for Marker models")

        if self.image_limit is not None:
            raise ValueError("image_limit parameter is not supported for Marker models")
        if self.image_min_size is not None:
            raise ValueError("image_min_size parameter is not supported for Marker models")

        del self.pages
        del self.bbox_annotation_format
        del self.document
        del self.document_annotation_format
        del self.image_limit
        del self.image_min_size
        del self.include_image_base64
        del self.model

        return self


class MarkerOCR(OCR):
    include_image_base64: bool | None = Field(default=None, description="Include image URLs in response")  # fmt: off
    format: Literal["markdown", "json", "html"]
    output: str
    images: dict[str, str]
    metadata: dict[str, Any]
    success: bool

    @model_validator(mode="before")
    def validate_model_before(cls, values):
        values["pages"] = []
        content = values.get("output", "")
        images = values.get("images", {})
        matches = list(re.finditer(r"\{[0-9]+\}-{48}\n\n", content))
        for i in range(len(matches)):
            offset = len(content) if i == len(matches) - 1 else matches[i + 1].span()[0]
            markdown = content[matches[i].span()[1] : offset]
            images_page = [
                OCRImageObject(id=key, image_base64=f"data:image/jpeg;base64,{value}" if values.get("include_image_base64") else None)
                for key, value in images.items()
                if key.startswith(f"_page_{i}_")
            ]
            values["pages"].append(OCRPageObject(index=i, markdown=markdown, images=images_page))

        values["usage_info"] = OCRUsage(doc_size_bytes=values.get("usage_info", {}).get("doc_size_bytes"), pages_processed=len(matches))
        return values

    @model_validator(mode="after")
    def validate_model_after(self):
        del self.format
        del self.output
        del self.images
        del self.metadata
        del self.success
        del self.include_image_base64

        return self
