# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Optional
from typing_extensions import Required, TypedDict

from .._types import SequenceNotStr

__all__ = ["RerankCreateParams"]


class RerankCreateParams(TypedDict, total=False):
    model: Required[str]
    """
    The model to use for the reranking, call `/v1/models` endpoint to get the list
    of available models, only `text-classification` model type is supported.
    """

    documents: Optional[SequenceNotStr[str]]
    """A list of texts that will be compared to the query and ranked by relevance.

    `documents` and `input` cannot both be provided.
    """

    input: Optional[SequenceNotStr[str]]
    """List of input texts to rerank by relevance to the prompt.

    `documents` and `input` cannot both be provided.
    """

    prompt: Optional[str]
    """The prompt to use for the reranking.

    `query` and `prompt` cannot both be provided.
    """

    query: Optional[str]
    """The search query to use for the reranking.

    `query` and `prompt` cannot both be provided.
    """

    top_n: Optional[int]
    """The number of top results to return.

    If set to None, all results will be returned.
    """
