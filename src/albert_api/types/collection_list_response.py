# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import Union
from typing_extensions import TypeAlias

from .collection import Collection
from .collections import Collections

__all__ = ["CollectionListResponse"]

CollectionListResponse: TypeAlias = Union[Collection, Collections]
