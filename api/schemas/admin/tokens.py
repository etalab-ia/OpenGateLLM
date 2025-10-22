import datetime as dt
from typing import Literal

from pydantic import Field, constr, field_validator

from api.schemas import BaseModel


class TokensResponse(BaseModel):
    id: int
    token: str


class TokenRequest(BaseModel):
    name: constr(strip_whitespace=True, min_length=1)
    user: int = Field(description="User ID to create the token for another user (by default, the current user). Required CREATE_USER permission.")  # fmt: off
    expires_at: int | None = Field(None, description="Timestamp in seconds")

    @field_validator("expires_at", mode="before")
    def must_be_future(cls, expires_at):
        if isinstance(expires_at, int):
            if expires_at <= int(dt.datetime.now(tz=dt.UTC).timestamp()):
                raise ValueError("Wrong timestamp, must be in the future.")

        return expires_at


class Token(BaseModel):
    object: Literal["token"] = "token"
    id: int
    name: str
    token: str
    user: int
    expires_at: int | None = None
    created_at: int


class Tokens(BaseModel):
    object: Literal["list"] = "list"
    data: list[Token]


class OAuth2LogoutRequest(BaseModel):
    proconnect_token: str | None = Field(default=None, description="ProConnect ID token used for logout")

    @field_validator("proconnect_token", mode="after")
    def validate_token(cls, token):
        if token is not None and token.strip() == "":
            raise ValueError("ProConnect token cannot be empty")
        return token.strip() if token else None
