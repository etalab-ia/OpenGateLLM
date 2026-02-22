# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing_extensions import Required, TypedDict

from .._types import FileTypes

__all__ = ["ParseBetaParseParams"]


class ParseBetaParseParams(TypedDict, total=False):
    file: Required[FileTypes]
    """The file to parse."""

    force_ocr: bool
    """Force OCR on all pages of the PDF.

    Defaults to False. This can lead to worse results if you have good text in your
    PDFs (which is true in most cases).
    """

    page_range: str
    """Page range to convert, specify comma separated page numbers or ranges.

    Example: '0,5-10,20'
    """
