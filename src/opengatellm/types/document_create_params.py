# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Optional
from typing_extensions import Literal, TypedDict

from .._types import FileTypes, SequenceNotStr

__all__ = ["DocumentCreateParams"]


class DocumentCreateParams(TypedDict, total=False):
    chunk_min_size: int
    """The minimum size in characters of the chunks to use for the upload file."""

    chunk_overlap: int
    """The overlap in characters of the chunks to use for the upload file."""

    chunk_size: int
    """The size in characters of the chunks to use for the upload file.

    If not provided, the document will not be split into chunks.
    """

    collection: Optional[int]

    collection_id: Optional[int]
    """The collection ID to use for the file upload.

    The file will be vectorized with model defined by the collection.
    """

    disable_chunking: bool
    """
    Whether to disable `RecursiveCharacterTextSplitter` chunking for the upload
    file.
    """

    file: Optional[FileTypes]
    """The file to create a document from.

    If not provided, the document will be created without content, use POST
    `/v1/documents/{document_id}/chunks` to fill it.
    """

    is_separator_regex: bool
    """Whether the separator is a regex to use for the upload file."""

    metadata: str
    """Optional additional metadata to add to each chunk if a file is provided.

    Provide a stringified JSON object matching the Metadata schema.
    """

    name: Optional[str]
    """Name of document if no file is provided or to override file name."""

    preset_separators: Literal[
        "cpp",
        "go",
        "java",
        "kotlin",
        "js",
        "ts",
        "php",
        "proto",
        "python",
        "r",
        "rst",
        "ruby",
        "rust",
        "scala",
        "swift",
        "markdown",
        "latex",
        "html",
        "sol",
        "csharp",
        "cobol",
        "c",
        "lua",
        "perl",
        "haskell",
        "elixir",
        "powershell",
        "visualbasic6",
    ]
    """Preset separators used by RecursiveCharacterTextSplitter for further splitting.

    See
    [implemented details](https://github.com/langchain-ai/langchain/blob/eb122945832eae9b9df7c70ccd8d51fcd7a1899b/libs/text-splitters/langchain_text_splitters/character.py#L164).
    """

    separators: SequenceNotStr[str]
    """Delimiters used by RecursiveCharacterTextSplitter for further splitting.

    If provided, `preset_separators` is ignored.
    """
