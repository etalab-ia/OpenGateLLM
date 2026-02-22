# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Union, Iterable, Optional
from typing_extensions import Literal, Required, TypeAlias, TypedDict

__all__ = [
    "ChatCompletionCreateParams",
    "Message",
    "MessageChatCompletionSystemMessageParam",
    "MessageChatCompletionSystemMessageParamContentUnionMember1",
    "MessageChatCompletionUserMessageParam",
    "MessageChatCompletionUserMessageParamContentUnionMember1",
    "MessageChatCompletionUserMessageParamContentUnionMember1ChatCompletionContentPartTextParam",
    "MessageChatCompletionUserMessageParamContentUnionMember1ChatCompletionContentPartImageParam",
    "MessageChatCompletionUserMessageParamContentUnionMember1ChatCompletionContentPartImageParamImageURL",
    "MessageChatCompletionAssistantMessageParam",
    "MessageChatCompletionAssistantMessageParamContentUnionMember1",
    "MessageChatCompletionAssistantMessageParamContentUnionMember1ChatCompletionContentPartTextParam",
    "MessageChatCompletionAssistantMessageParamContentUnionMember1ChatCompletionContentPartRefusalParam",
    "MessageChatCompletionAssistantMessageParamFunctionCall",
    "MessageChatCompletionAssistantMessageParamToolCall",
    "MessageChatCompletionAssistantMessageParamToolCallFunction",
    "MessageChatCompletionToolMessageParam",
    "MessageChatCompletionToolMessageParamContentUnionMember1",
    "MessageChatCompletionFunctionMessageParam",
    "ToolChoice",
    "ToolChoiceChatCompletionNamedToolChoiceParam",
    "ToolChoiceChatCompletionNamedToolChoiceParamFunction",
    "Tool",
    "ToolFunction",
]


class ChatCompletionCreateParams(TypedDict, total=False):
    messages: Required[Iterable[Message]]

    model: Required[str]

    best_of: Optional[int]

    frequency_penalty: Optional[float]

    max_tokens: Optional[int]

    min_p: float

    n: Optional[int]

    presence_penalty: Optional[float]

    seed: Optional[int]

    stop: Union[str, List[str], None]

    stream: Optional[Literal[True, False]]

    temperature: Optional[float]

    tool_choice: Optional[ToolChoice]

    tools: Iterable[Tool]

    top_k: int

    top_p: Optional[float]

    user: Optional[str]


class MessageChatCompletionSystemMessageParamContentUnionMember1(TypedDict, total=False):
    text: Required[str]

    type: Required[Literal["text"]]


class MessageChatCompletionSystemMessageParam(TypedDict, total=False):
    content: Required[Union[str, Iterable[MessageChatCompletionSystemMessageParamContentUnionMember1]]]

    role: Required[Literal["system"]]

    name: str


class MessageChatCompletionUserMessageParamContentUnionMember1ChatCompletionContentPartTextParam(
    TypedDict, total=False
):
    text: Required[str]

    type: Required[Literal["text"]]


class MessageChatCompletionUserMessageParamContentUnionMember1ChatCompletionContentPartImageParamImageURL(
    TypedDict, total=False
):
    url: Required[str]

    detail: Literal["auto", "low", "high"]


class MessageChatCompletionUserMessageParamContentUnionMember1ChatCompletionContentPartImageParam(
    TypedDict, total=False
):
    image_url: Required[
        MessageChatCompletionUserMessageParamContentUnionMember1ChatCompletionContentPartImageParamImageURL
    ]

    type: Required[Literal["image_url"]]


MessageChatCompletionUserMessageParamContentUnionMember1: TypeAlias = Union[
    MessageChatCompletionUserMessageParamContentUnionMember1ChatCompletionContentPartTextParam,
    MessageChatCompletionUserMessageParamContentUnionMember1ChatCompletionContentPartImageParam,
]


class MessageChatCompletionUserMessageParam(TypedDict, total=False):
    content: Required[Union[str, Iterable[MessageChatCompletionUserMessageParamContentUnionMember1]]]

    role: Required[Literal["user"]]

    name: str


class MessageChatCompletionAssistantMessageParamContentUnionMember1ChatCompletionContentPartTextParam(
    TypedDict, total=False
):
    text: Required[str]

    type: Required[Literal["text"]]


class MessageChatCompletionAssistantMessageParamContentUnionMember1ChatCompletionContentPartRefusalParam(
    TypedDict, total=False
):
    refusal: Required[str]

    type: Required[Literal["refusal"]]


MessageChatCompletionAssistantMessageParamContentUnionMember1: TypeAlias = Union[
    MessageChatCompletionAssistantMessageParamContentUnionMember1ChatCompletionContentPartTextParam,
    MessageChatCompletionAssistantMessageParamContentUnionMember1ChatCompletionContentPartRefusalParam,
]


class MessageChatCompletionAssistantMessageParamFunctionCall(TypedDict, total=False):
    arguments: Required[str]

    name: Required[str]


class MessageChatCompletionAssistantMessageParamToolCallFunction(TypedDict, total=False):
    arguments: Required[str]

    name: Required[str]


class MessageChatCompletionAssistantMessageParamToolCall(TypedDict, total=False):
    id: Required[str]

    function: Required[MessageChatCompletionAssistantMessageParamToolCallFunction]

    type: Required[Literal["function"]]


class MessageChatCompletionAssistantMessageParam(TypedDict, total=False):
    role: Required[Literal["assistant"]]

    content: Union[str, Iterable[MessageChatCompletionAssistantMessageParamContentUnionMember1], None]

    function_call: Optional[MessageChatCompletionAssistantMessageParamFunctionCall]

    name: str

    refusal: Optional[str]

    tool_calls: Iterable[MessageChatCompletionAssistantMessageParamToolCall]


class MessageChatCompletionToolMessageParamContentUnionMember1(TypedDict, total=False):
    text: Required[str]

    type: Required[Literal["text"]]


class MessageChatCompletionToolMessageParam(TypedDict, total=False):
    content: Required[Union[str, Iterable[MessageChatCompletionToolMessageParamContentUnionMember1]]]

    role: Required[Literal["tool"]]

    tool_call_id: Required[str]


class MessageChatCompletionFunctionMessageParam(TypedDict, total=False):
    content: Required[Optional[str]]

    name: Required[str]

    role: Required[Literal["function"]]


Message: TypeAlias = Union[
    MessageChatCompletionSystemMessageParam,
    MessageChatCompletionUserMessageParam,
    MessageChatCompletionAssistantMessageParam,
    MessageChatCompletionToolMessageParam,
    MessageChatCompletionFunctionMessageParam,
]


class ToolChoiceChatCompletionNamedToolChoiceParamFunction(TypedDict, total=False):
    name: Required[str]


class ToolChoiceChatCompletionNamedToolChoiceParam(TypedDict, total=False):
    function: Required[ToolChoiceChatCompletionNamedToolChoiceParamFunction]

    type: Required[Literal["function"]]


ToolChoice: TypeAlias = Union[
    Literal["none"], Literal["none", "auto", "required"], ToolChoiceChatCompletionNamedToolChoiceParam
]


class ToolFunction(TypedDict, total=False):
    name: Required[str]

    description: str

    parameters: object

    strict: Optional[bool]


class Tool(TypedDict, total=False):
    function: Required[ToolFunction]

    type: Required[Literal["function"]]
