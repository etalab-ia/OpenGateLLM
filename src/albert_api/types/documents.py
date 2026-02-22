# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import List, Optional
from typing_extensions import Literal

from .._models import BaseModel

__all__ = ["Documents", "Data"]


class Data(BaseModel):
    id: str

    chunks: int

    created_at: int

    name: str

    object: Optional[Literal["document"]] = None


class Documents(BaseModel):
    data: List[Data]

    object: Optional[Literal["list"]] = None
