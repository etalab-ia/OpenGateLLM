from pydantic import ConfigDict

from api.domain import BaseModel
from api.domain.role.entities import LimitType


class RouterLimitView(BaseModel):
    """Read model of one rate limit of a router, and what is left of it."""

    model_config = ConfigDict(frozen=True)

    type: LimitType
    value: int | None
    remaining: int


class RouterLimitsView(BaseModel):
    """Read model of the rate limits of a router the user is allowed to use."""

    model_config = ConfigDict(frozen=True)

    router_id: int
    model: str
    limits: list[RouterLimitView]
