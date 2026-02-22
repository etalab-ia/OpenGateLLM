# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import Optional
from typing_extensions import Literal

from .._models import BaseModel

__all__ = ["Collection"]


class Collection(BaseModel):
    id: str

    created_at: Optional[int] = None

    description: Optional[str] = None

    documents: Optional[int] = None

    model: Optional[str] = None

    name: Optional[str] = None

    type: Optional[Literal["public", "private"]] = None

    user: Optional[str] = None
