from datetime import UTC, datetime
from typing import Literal

from pydantic import Field

from api.schemas import BaseModel


class Organization(BaseModel):
    object: Literal["organization"] = "organization"
    id: int
    name: str
    users: int
    created: int = Field(default_factory=lambda: int(datetime.now(tz=UTC).timestamp()), description="Time of creation, as Unix timestamp.")
    updated: int = Field(default_factory=lambda: int(datetime.now(tz=UTC).timestamp()), description="Time of last update, as Unix timestamp.")


class Organizations(BaseModel):
    object: Literal["list"] = "list"
    data: list[Organization]
