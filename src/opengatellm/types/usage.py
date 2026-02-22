# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import TYPE_CHECKING, Dict, Optional

from pydantic import Field as FieldInfo

from .._models import BaseModel

__all__ = ["Usage", "Carbon", "CarbonKgCo2eq", "CarbonKWh"]


class CarbonKgCo2eq(BaseModel):
    max: Optional[float] = None
    """Maximum carbon footprint in kgCO2eq (global warming potential)."""

    min: Optional[float] = None
    """Minimum carbon footprint in kgCO2eq (global warming potential)."""

    if TYPE_CHECKING:
        # Some versions of Pydantic <2.8.0 have a bug and don’t allow assigning a
        # value to this field, so for compatibility we avoid doing it at runtime.
        __pydantic_extra__: Dict[str, object] = FieldInfo(init=False)  # pyright: ignore[reportIncompatibleVariableOverride]

        # Stub to indicate that arbitrary properties are accepted.
        # To access properties that are not valid identifiers you can use `getattr`, e.g.
        # `getattr(obj, '$type')`
        def __getattr__(self, attr: str) -> object: ...
    else:
        __pydantic_extra__: Dict[str, object]


class CarbonKWh(BaseModel):
    max: Optional[float] = None
    """Maximum carbon footprint in kWh."""

    min: Optional[float] = None
    """Minimum carbon footprint in kWh."""

    if TYPE_CHECKING:
        # Some versions of Pydantic <2.8.0 have a bug and don’t allow assigning a
        # value to this field, so for compatibility we avoid doing it at runtime.
        __pydantic_extra__: Dict[str, object] = FieldInfo(init=False)  # pyright: ignore[reportIncompatibleVariableOverride]

        # Stub to indicate that arbitrary properties are accepted.
        # To access properties that are not valid identifiers you can use `getattr`, e.g.
        # `getattr(obj, '$type')`
        def __getattr__(self, attr: str) -> object: ...
    else:
        __pydantic_extra__: Dict[str, object]


class Carbon(BaseModel):
    kg_co2eq: Optional[CarbonKgCo2eq] = FieldInfo(alias="kgCO2eq", default=None)

    k_wh: Optional[CarbonKWh] = FieldInfo(alias="kWh", default=None)

    if TYPE_CHECKING:
        # Some versions of Pydantic <2.8.0 have a bug and don’t allow assigning a
        # value to this field, so for compatibility we avoid doing it at runtime.
        __pydantic_extra__: Dict[str, object] = FieldInfo(init=False)  # pyright: ignore[reportIncompatibleVariableOverride]

        # Stub to indicate that arbitrary properties are accepted.
        # To access properties that are not valid identifiers you can use `getattr`, e.g.
        # `getattr(obj, '$type')`
        def __getattr__(self, attr: str) -> object: ...
    else:
        __pydantic_extra__: Dict[str, object]


class Usage(BaseModel):
    carbon: Optional[Carbon] = None

    completion_tokens: Optional[int] = None
    """Number of completion tokens (e.g. output tokens)."""

    cost: Optional[float] = None
    """Total cost of the request."""

    prompt_tokens: Optional[int] = None
    """Number of prompt tokens (e.g. input tokens)."""

    requests: Optional[int] = None
    """Number of model requests."""

    total_tokens: Optional[int] = None
    """Total number of tokens (e.g. input and output tokens)."""

    if TYPE_CHECKING:
        # Some versions of Pydantic <2.8.0 have a bug and don’t allow assigning a
        # value to this field, so for compatibility we avoid doing it at runtime.
        __pydantic_extra__: Dict[str, object] = FieldInfo(init=False)  # pyright: ignore[reportIncompatibleVariableOverride]

        # Stub to indicate that arbitrary properties are accepted.
        # To access properties that are not valid identifiers you can use `getattr`, e.g.
        # `getattr(obj, '$type')`
        def __getattr__(self, attr: str) -> object: ...
    else:
        __pydantic_extra__: Dict[str, object]
