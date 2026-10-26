from typing import Annotated, Literal

from pydantic import Field

from api.domain import BaseModel
from api.infrastructure.fastapi.schemas.admin.roles import LimitType


class LimitResponse(BaseModel):
    object: Annotated[Literal["limit"], Field(default="limit", description="The limit object type.")]
    router_id: Annotated[int, Field(description="The router ID.")]
    model: Annotated[str, Field(description="The model name, as listed by the models endpoint.")]
    type: Annotated[LimitType, Field(description="The limit type.")]
    value: Annotated[int | None, Field(description="The limit value. If None, the limit is unlimited.")]
    remaining: Annotated[int, Field(description="What is left of the limit in the current window. Not tracked when `value` is None: check `value` first.")]  # fmt: off


class LimitsResponse(BaseModel):
    object: Annotated[Literal["list"], Field(default="list", description="The list object type.")]
    data: Annotated[list[LimitResponse], Field(description="The rate limits of the models the user is allowed to use.")]
