from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_validator

from api.domain import BaseModel
from api.infrastructure.fastapi.schemas import UnixTimestamp


class CreateKeyBody(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(description="Name of the key.", examples=["key-1"])]  # fmt: off
    user: Annotated[int, Field(description="User ID to create the token for another user (by default, the current user). Required CREATE_USER permission.")]  # fmt: off
    expires: Annotated[int | None, Field(default=None, description="Expiration time, as Unix timestamp. If None, the key never expires.")]

    @field_validator("expires", mode="after")
    def must_be_future_and_convert_to_datetime(cls, expires) -> None | datetime:
        if expires is None:
            return expires

        if expires <= int(datetime.now(tz=UTC).timestamp()):
            raise ValueError("Expiration time must be in the future.")

        expires = datetime.fromtimestamp(timestamp=expires, tz=UTC)

        return expires


class KeyResponse(BaseModel):
    object: Annotated[Literal["key"], Field(default="key", description="Type of the object.")]
    id: Annotated[int, Field(description="ID of the key.")]
    name: Annotated[str, Field(description="Name of the key.")]
    value: Annotated[str, Field(description="Value of the key.")]
    user_id: Annotated[int, Field(description="ID of the user that owns the key.")]
    expires: Annotated[UnixTimestamp | None, Field(default=None, description="Time of expiration, as Unix timestamp. If None, the key never expires.")]  # fmt: off
    created: Annotated[UnixTimestamp, Field(description="Time of creation, as Unix timestamp.")]


class KeysResponse(BaseModel):
    object: Annotated[Literal["list"], Field(default="list", description="Type of the object.")]
    total: Annotated[int, Field(description="Total number of keys.")]
    offset: Annotated[int, Field(description="Offset of the keys list.")]
    limit: Annotated[int, Field(description="Limit of the keys list.")]
    data: Annotated[list[KeyResponse], Field(description="List of keys.")]
