# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Dict, Union, Optional
from typing_extensions import Literal, Required, TypeAlias, TypedDict

__all__ = ["ResponseFormatParam", "JsonSchema"]


class JsonSchemaTyped(TypedDict, total=False):
    """The JSON schema definition. Required when type is 'json_schema'."""

    name: Required[str]
    """The name of the JSON schema."""

    schema_definition: Required[Dict[str, object]]
    """The JSON schema definition."""

    description: Optional[str]
    """Optional description of the schema."""

    strict: bool
    """Whether to use strict mode."""


JsonSchema: TypeAlias = Union[JsonSchemaTyped, Dict[str, object]]


class ResponseFormatParamTyped(TypedDict, total=False):
    json_schema: Optional[JsonSchema]
    """The JSON schema definition. Required when type is 'json_schema'."""

    type: Literal["text", "json_object", "json_schema"]
    """Specify the format that the model must output.

    By default it will use `{ "type": "text" }`. Setting to
    `{ "type": "json_object" }` enables JSON mode, which guarantees the message the
    model generates is in JSON. When using JSON mode you MUST also instruct the
    model to produce JSON yourself with a system or a user message. Setting to
    `{ "type": "json_schema" }` enables JSON schema mode, which guarantees the
    message the model generates is in JSON and follows the schema you provide.
    """


ResponseFormatParam: TypeAlias = Union[ResponseFormatParamTyped, Dict[str, object]]
