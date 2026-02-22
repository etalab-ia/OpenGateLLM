# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Optional
from typing_extensions import Literal, Required, TypedDict

from .._types import FileTypes

__all__ = ["FileCreateParams", "Request", "RequestChunker", "RequestChunkerArgs"]


class FileCreateParams(TypedDict, total=False):
    file: Required[FileTypes]

    request: Required[Request]


class RequestChunkerArgs(TypedDict, total=False):
    chunk_min_size: int

    chunk_overlap: int

    chunk_size: int

    is_separator_regex: bool

    length_function: Literal["len"]

    separators: List[str]


class RequestChunker(TypedDict, total=False):
    args: Optional[RequestChunkerArgs]

    name: Optional[Literal["LangchainRecursiveCharacterTextSplitter", "NoChunker"]]


class Request(TypedDict, total=False):
    collection: Required[str]

    chunker: Optional[RequestChunker]
