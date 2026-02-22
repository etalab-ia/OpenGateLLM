# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Dict, Union, Iterable, Optional
from typing_extensions import Required, TypedDict

from .._types import SequenceNotStr

__all__ = ["CompletionCreateParams"]


class CompletionCreateParams(TypedDict, total=False):
    model: Required[str]

    prompt: Required[Union[str, SequenceNotStr[str], Iterable[int], Iterable[Iterable[int]]]]

    best_of: Optional[int]

    echo: Optional[bool]

    frequency_penalty: Optional[float]

    logit_bias: Optional[Dict[str, float]]

    logprobs: Optional[int]

    max_tokens: Optional[int]

    n: Optional[int]

    presence_penalty: Optional[float]

    seed: Optional[int]

    stop: Union[str, SequenceNotStr[str], None]

    stream: Optional[bool]

    suffix: Optional[str]

    temperature: Optional[float]

    top_p: Optional[float]

    user: Optional[str]
