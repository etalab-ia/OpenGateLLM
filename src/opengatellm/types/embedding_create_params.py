# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Union, Iterable, Optional
from typing_extensions import Literal, Required, TypedDict

from .._types import SequenceNotStr

__all__ = ["EmbeddingCreateParams"]


class EmbeddingCreateParams(TypedDict, total=False):
    input: Required[Union[Iterable[int], Iterable[Iterable[int]], str, SequenceNotStr[str]]]
    """Input text to embed, encoded as a string or array of tokens.

    To embed multiple inputs in a single request, pass an array of strings or array
    of token arrays. The input must not exceed the max input tokens for the model
    (call `/v1/models` endpoint to get the `max_context_length` by model) and cannot
    be an empty string.
    """

    model: Required[str]
    """ID of the model to use.

    Call `/v1/models` endpoint to get the list of available models, only
    `text-embeddings-inference` model type is supported.
    """

    dimensions: Optional[int]
    """The number of dimensions the resulting output embeddings should have."""

    encoding_format: Optional[Literal["float"]]
    """The format of the output embeddings. Only `float` is supported."""
