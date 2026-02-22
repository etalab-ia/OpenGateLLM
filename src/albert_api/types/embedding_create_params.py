# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Union, Iterable, Optional
from typing_extensions import Literal, Required, TypedDict

__all__ = ["EmbeddingCreateParams"]


class EmbeddingCreateParams(TypedDict, total=False):
    input: Required[Union[Iterable[int], Iterable[Iterable[int]], str, List[str]]]

    model: Required[str]

    dimensions: Optional[int]

    encoding_format: Optional[Literal["float"]]

    user: Optional[str]
