# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

import builtins
from typing import TYPE_CHECKING, Optional
from typing_extensions import Literal

from .._models import BaseModel

__all__ = ["Model"]


class Model(BaseModel):
    id: str

    created: int

    object: Literal["model"]

    owned_by: str

    status: Literal["available", "unavailable"]

    type: Literal["text-generation", "text-embeddings-inference"]

    max_context_length: Optional[int] = None

    if TYPE_CHECKING:
        # Stub to indicate that arbitrary properties are accepted.
        # To access properties that are not valid identifiers you can use `getattr`, e.g.
        # `getattr(obj, '$type')`
        def __getattr__(self, attr: str) -> builtins.object: ...
