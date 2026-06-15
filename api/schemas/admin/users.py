import datetime as dt
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_validator

from api.schemas import BaseModel


class UsersResponse(BaseModel):
    id: int = Field(description="The user ID.")


class CreateUser(BaseModel):
    email: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=254)] = Field(description="The user email.")
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = Field(default=None, description="The user name.")
    password: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=72)] = Field(description="The user password.")
    role: int = Field(description="The role ID.")
    organization: int | None = Field(default=None, description="The organization ID.")
    budget: float | None = Field(default=None, description="The budget.")
    expires: int | None = Field(default=None, description="The expiration timestamp.")
    priority: int | None = Field(default=0, ge=0, description="The user priority. Higher value means higher priority. 0 is default.")  # fmt: off

    @field_validator("expires", mode="before")
    def must_be_future(cls, expires):
        if isinstance(expires, int):
            if expires <= int(dt.datetime.now(tz=dt.UTC).timestamp()):
                raise ValueError("Wrong timestamp, must be in the future.")

        return expires


class User(BaseModel):
    object: Literal["user"] = Field(default="user", description="The user object type.")
    id: int = Field(description="The user ID.")
    email: str = Field(description="The user email.")
    name: str | None = Field(default=None, description="The user name.")
    sub: str | None = Field(default=None, description="The user subject identifier. Null when using email/password auth.")
    iss: str | None = Field(default=None, description="The user issuer identifier. Null when using email/password auth.")
    role: int = Field(description="The user role ID.")
    organization: int | None = Field(default=None, description="The user organization ID.")
    budget: float | None = Field(default=None, description="The user budget. If None, the user has unlimited budget.")
    expires: int | None = Field(default=None, description="The user expiration timestamp. If None, the user will never expire.")
    created: int = Field(description="The user creation timestamp.")
    updated: int = Field(description="The user update timestamp.")
    priority: int = Field(description="The user priority (higher = higher priority).")


class Users(BaseModel):
    object: Literal["list"] = Field(default="list", description="The users list object type.")
    data: list[User] = Field(description="The users list.")
