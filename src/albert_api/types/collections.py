# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import List, Optional
from typing_extensions import Literal

from .._models import BaseModel
from .collection import Collection

__all__ = ["Collections"]


class Collections(BaseModel):
    data: List[Collection]

    object: Optional[Literal["list"]] = None
