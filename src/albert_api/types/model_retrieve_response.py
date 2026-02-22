# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import Union
from typing_extensions import TypeAlias

from .model import Model
from .models import Models

__all__ = ["ModelRetrieveResponse"]

ModelRetrieveResponse: TypeAlias = Union[Models, Model]
