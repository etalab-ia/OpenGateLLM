from typing import Literal

from fastapi import File, Form, UploadFile
from fastapi.exceptions import RequestValidationError
from pydantic import Field, ValidationError, field_validator

from api.schemas import BaseModel
from api.schemas.usage import Usage
from api.utils.exceptions import FileSizeLimitExceededException


class ParsedDocumentMetadata(BaseModel):
    document_name: str
    page: int = 0


class ParsedDocumentPage(BaseModel):
    object: Literal["documentPage"] = "documentPage"
    content: str
    images: dict[str, str]
    metadata: ParsedDocumentMetadata


class ParsedDocument(BaseModel):
    object: Literal["list"] = "list"
    data: list[ParsedDocumentPage]
    usage: Usage = Field(default_factory=Usage, description="Usage information for the request.")


class CreateParseForm(BaseModel):
    file: UploadFile
    page_range: str
    force_ocr: bool

    @classmethod
    def as_form(
        cls,
        file: UploadFile = File(default=..., description="The file to parse."),
        page_range: str = Form(default="", description="Page range to convert, specify comma separated page numbers or ranges. Example: '0,5-10,20'"),
        force_ocr: bool = Form(
            default=False,
            description="Force OCR on all pages of the PDF. Defaults to False. This can lead to worse results if you have good text in your PDFs (which is true in most cases).",
        ),
    ) -> "CreateParseForm":
        try:
            return cls(file=file, page_range=page_range, force_ocr=force_ocr)
        except ValidationError as exc:
            raise RequestValidationError(exc.errors())

    @field_validator("file")
    def validate_file(cls, file: UploadFile) -> UploadFile:
        if file.size > FileSizeLimitExceededException.MAX_CONTENT_SIZE:
            raise FileSizeLimitExceededException()
        return file
