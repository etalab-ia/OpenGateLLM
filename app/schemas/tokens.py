import datetime as dt
from typing import Literal, Optional

from pydantic import Field, constr, field_validator

from app.schemas import BaseModel
from app.schemas.admin.tokens import Tokens as AdminTokens
from app.schemas.admin.tokens import TokensResponse as AdminTokensResponse


class TokensResponse(AdminTokensResponse):
    pass


class TokenRequest(BaseModel):
    name: constr(strip_whitespace=True, min_length=1)
    expires_at: Optional[int] = Field(None, description="Timestamp in seconds")

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
    expires_at: Optional[int] = None
    created_at: int


class Tokens(AdminTokens):
    pass
