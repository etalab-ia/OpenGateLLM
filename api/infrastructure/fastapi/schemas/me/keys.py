from datetime import UTC, datetime
from typing import Annotated

from pydantic import Field, StringConstraints, field_validator

from api.domain import BaseModel


class CreateKeyBody(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(description="Name of the key.", examples=["key-1"])]  # fmt: off
    expires: Annotated[
        int | None,
        Field(
            default=None,
            description="Expiration time, as Unix timestamp. If None, uses the configured maximum key lifetime when set, otherwise the key never expires.",
        ),
    ]

    @field_validator("expires", mode="after")
    def must_be_future_and_convert_to_datetime(cls, expires) -> None | datetime:
        if expires is None:
            return expires

        if expires <= int(datetime.now(tz=UTC).timestamp()):
            raise ValueError("Expiration time must be in the future.")

        expires = datetime.fromtimestamp(timestamp=expires, tz=UTC)

        return expires
