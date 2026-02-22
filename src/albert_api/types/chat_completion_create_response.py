# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import Union
from typing_extensions import TypeAlias

from .chat_completion import ChatCompletion
from .chat_completion_chunk import ChatCompletionChunk

__all__ = ["ChatCompletionCreateResponse"]

ChatCompletionCreateResponse: TypeAlias = Union[ChatCompletion, ChatCompletionChunk]
