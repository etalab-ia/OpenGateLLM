# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Dict, Union, Iterable, Optional
from typing_extensions import Literal, Required, TypeAlias, TypedDict

from .response_format_param import ResponseFormatParam

__all__ = [
    "OcrExtractTextParams",
    "Document",
    "DocumentDocumentURLChunk",
    "DocumentImageURLChunk",
    "DocumentImageURLChunkImageURL",
    "DocumentImageURLChunkImageURLImageURL",
]


class OcrExtractTextParams(TypedDict, total=False):
    document: Required[Document]
    """Document to run OCR on."""

    bbox_annotation_format: Optional[ResponseFormatParam]
    """Specify the format that the model must output for the bounding boxes.

    By default it will use `{ "type": "text" }`. Setting to
    `{ "type": "json_object" }` enables JSON mode, which guarantees the message the
    model generates is in JSON. When using JSON mode you MUST also instruct the
    model to produce JSON yourself with a system or a user message. Setting to
    `{ "type": "json_schema" }` enables JSON schema mode, which guarantees the
    message the model generates is in JSON and follows the schema you provide.
    """

    document_annotation_format: Optional[ResponseFormatParam]
    """Specify the format that the model must output for the document.

    By default it will use `{ "type": "text" }`. Setting to
    `{ "type": "json_object" }` enables JSON mode, which guarantees the message the
    model generates is in JSON. When using JSON mode you MUST also instruct the
    model to produce JSON yourself with a system or a user message. Setting to
    `{ "type": "json_schema" }` enables JSON schema mode, which guarantees the
    message the model generates is in JSON and follows the schema you provide.
    """

    image_limit: Optional[int]
    """Max images to extract"""

    image_min_size: Optional[int]
    """Minimum height and width of image to extract"""

    include_image_base64: Optional[bool]
    """Include image URLs in response"""

    model: Optional[str]
    """The model to use for the OCR."""

    pages: Optional[Iterable[int]]
    """
    Specific pages user wants to process in various formats: single number, range,
    or list of both. Starts from 0
    """


class DocumentDocumentURLChunkTyped(TypedDict, total=False):
    document_url: Required[str]
    """The URL of the document."""

    document_name: Optional[str]
    """The filename of the document."""

    type: Literal["document_url"]
    """The type of the document."""


DocumentDocumentURLChunk: TypeAlias = Union[DocumentDocumentURLChunkTyped, Dict[str, object]]


class DocumentImageURLChunkImageURLImageURLTyped(TypedDict, total=False):
    url: Required[str]
    """The URL of the image."""

    detail: Optional[str]
    """The detail of the image."""


DocumentImageURLChunkImageURLImageURL: TypeAlias = Union[DocumentImageURLChunkImageURLImageURLTyped, Dict[str, object]]

DocumentImageURLChunkImageURL: TypeAlias = Union[DocumentImageURLChunkImageURLImageURL, str]


class DocumentImageURLChunkTyped(TypedDict, total=False):
    image_url: Required[DocumentImageURLChunkImageURL]
    """The URL of the image to OCR."""

    type: Literal["image_url"]
    """The type of the image."""


DocumentImageURLChunk: TypeAlias = Union[DocumentImageURLChunkTyped, Dict[str, object]]

Document: TypeAlias = Union[DocumentDocumentURLChunk, DocumentImageURLChunk]
