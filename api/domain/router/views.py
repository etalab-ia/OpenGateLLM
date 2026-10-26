from pydantic import ConfigDict

from api.domain import BaseModel
from api.domain.role.entities import LimitType


class RouterLimitView(BaseModel):
    """Read model of one rate limit of a router the user is allowed to use."""

    model_config = ConfigDict(frozen=True)

    router_id: int
    model: str
    type: LimitType
    value: int | None
    remaining: int
