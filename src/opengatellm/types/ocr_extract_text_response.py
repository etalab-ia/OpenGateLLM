# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import TYPE_CHECKING, Dict, List, Optional

from pydantic import Field as FieldInfo

from .usage import Usage
from .._models import BaseModel

__all__ = ["OcrExtractTextResponse", "Page", "PageImage", "PageDimensions", "UsageInfo"]


class PageImage(BaseModel):
    id: str
    """Image ID for extracted image in a page"""

    bottom_right_x: Optional[int] = None
    """X coordinate of bottom-right corner of the extracted image"""

    bottom_right_y: Optional[int] = None
    """Y coordinate of bottom-right corner of the extracted image"""

    image_annotation: Optional[str] = None
    """Annotation of the extracted image in json str"""

    image_base64: Optional[str] = None
    """Base64 string of the extracted image"""

    top_left_x: Optional[int] = None
    """X coordinate of top-left corner of the extracted image"""

    top_left_y: Optional[int] = None
    """Y coordinate of top-left corner of the extracted image"""

    if TYPE_CHECKING:
        # Some versions of Pydantic <2.8.0 have a bug and don’t allow assigning a
        # value to this field, so for compatibility we avoid doing it at runtime.
        __pydantic_extra__: Dict[str, object] = FieldInfo(init=False)  # pyright: ignore[reportIncompatibleVariableOverride]

        # Stub to indicate that arbitrary properties are accepted.
        # To access properties that are not valid identifiers you can use `getattr`, e.g.
        # `getattr(obj, '$type')`
        def __getattr__(self, attr: str) -> object: ...
    else:
        __pydantic_extra__: Dict[str, object]


class PageDimensions(BaseModel):
    """The dimensions of the PDF Page's screenshot image"""

    dpi: int
    """Dots per inch of the page-image"""

    height: int
    """Height of the image in pixels"""

    width: int
    """Width of the image in pixels"""

    if TYPE_CHECKING:
        # Some versions of Pydantic <2.8.0 have a bug and don’t allow assigning a
        # value to this field, so for compatibility we avoid doing it at runtime.
        __pydantic_extra__: Dict[str, object] = FieldInfo(init=False)  # pyright: ignore[reportIncompatibleVariableOverride]

        # Stub to indicate that arbitrary properties are accepted.
        # To access properties that are not valid identifiers you can use `getattr`, e.g.
        # `getattr(obj, '$type')`
        def __getattr__(self, attr: str) -> object: ...
    else:
        __pydantic_extra__: Dict[str, object]


class Page(BaseModel):
    images: List[PageImage]
    """List of all extracted images in the page."""

    index: int
    """The page index in a pdf document starting from 0"""

    dimensions: Optional[PageDimensions] = None
    """The dimensions of the PDF Page's screenshot image"""

    markdown: Optional[str] = None
    """The markdown string response of the page"""

    if TYPE_CHECKING:
        # Some versions of Pydantic <2.8.0 have a bug and don’t allow assigning a
        # value to this field, so for compatibility we avoid doing it at runtime.
        __pydantic_extra__: Dict[str, object] = FieldInfo(init=False)  # pyright: ignore[reportIncompatibleVariableOverride]

        # Stub to indicate that arbitrary properties are accepted.
        # To access properties that are not valid identifiers you can use `getattr`, e.g.
        # `getattr(obj, '$type')`
        def __getattr__(self, attr: str) -> object: ...
    else:
        __pydantic_extra__: Dict[str, object]


class UsageInfo(BaseModel):
    """Usage information for the request."""

    pages_processed: int
    """Number of pages processed"""

    doc_size_bytes: Optional[int] = None
    """Document size in bytes"""

    if TYPE_CHECKING:
        # Some versions of Pydantic <2.8.0 have a bug and don’t allow assigning a
        # value to this field, so for compatibility we avoid doing it at runtime.
        __pydantic_extra__: Dict[str, object] = FieldInfo(init=False)  # pyright: ignore[reportIncompatibleVariableOverride]

        # Stub to indicate that arbitrary properties are accepted.
        # To access properties that are not valid identifiers you can use `getattr`, e.g.
        # `getattr(obj, '$type')`
        def __getattr__(self, attr: str) -> object: ...
    else:
        __pydantic_extra__: Dict[str, object]


class OcrExtractTextResponse(BaseModel):
    pages: List[Page]
    """List of OCR info for pages."""

    id: Optional[str] = None
    """The ID of the OCR request."""

    document_annotation: Optional[str] = None
    """Formatted response in the request_format if provided in json str"""

    model: Optional[str] = None
    """The model used to generate the OCR."""

    usage: Optional[Usage] = None
    """Usage information for the request."""

    usage_info: Optional[UsageInfo] = None
    """Usage information for the request."""

    if TYPE_CHECKING:
        # Some versions of Pydantic <2.8.0 have a bug and don’t allow assigning a
        # value to this field, so for compatibility we avoid doing it at runtime.
        __pydantic_extra__: Dict[str, object] = FieldInfo(init=False)  # pyright: ignore[reportIncompatibleVariableOverride]

        # Stub to indicate that arbitrary properties are accepted.
        # To access properties that are not valid identifiers you can use `getattr`, e.g.
        # `getattr(obj, '$type')`
        def __getattr__(self, attr: str) -> object: ...
    else:
        __pydantic_extra__: Dict[str, object]
