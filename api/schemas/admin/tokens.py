import datetime as dt
from typing import Literal

from pydantic import Field, constr, field_validator, model_validator

from api.schemas import BaseModel


class TokensResponse(BaseModel):
    id: int
    token: str


class CreateToken(BaseModel):
    name: constr(strip_whitespace=True, min_length=1) = Field(..., description="The name of the token.")
    user: int | None = Field(None, description="User ID of the user to create the token for. Optional if email is provided.")
    email: str | None = Field(None, description="Email of the user to create the token for. Optional if user is provided.")
    expires: int | None = Field(None, description="Timestamp in seconds for the token expiration.")

    @field_validator("expires", mode="before")
    def must_be_future(cls, expires):
        # @TODO: replace by Pydantic FutureDatetime
        if isinstance(expires, int):
            if expires <= int(dt.datetime.now(tz=dt.UTC).timestamp()):
                raise ValueError("Wrong timestamp, must be in the future.")

        return expires

    @model_validator(mode="after")
    def validate_user_or_email(self):
        if self.user is None and self.email is None:
            raise ValueError("Either user or email must be provided.")

        return self


class Token(BaseModel):
    object: Literal["token"] = "token"
    id: int
    name: str
    token: str
    user: int
    expires: int | None = None
    created: int


class Tokens(BaseModel):
    object: Literal["list"] = "list"
    data: list[Token]
