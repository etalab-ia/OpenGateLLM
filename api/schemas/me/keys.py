import datetime as dt
from typing import Annotated, Literal

from pydantic import Field, constr, field_validator

from api.schemas import BaseModel


class CreateKeyResponse(BaseModel):
    id: int
    token: str


class CreateKey(BaseModel):
    name: Annotated[str, constr(strip_whitespace=True, min_length=1)]
    expires: int | None = Field(None, description="Timestamp in seconds")

    @field_validator("expires", mode="before")
    def must_be_future(cls, expires):
        if isinstance(expires, int):
            if expires <= int(dt.datetime.now(tz=dt.UTC).timestamp()):
                raise ValueError("Wrong timestamp, must be in the future.")

        return expires


class Key(BaseModel):
    object: Literal["key"] = "key"
    id: int
    name: str
    token: str
    expires: int | None = None
    created: int


class Keys(BaseModel):
    object: Literal["list"] = "list"
    data: list[Key]
