import datetime as dt
from typing import List, Literal, Optional

from pydantic import Field, constr, field_validator

from api.schemas import BaseModel


class UserUpdateRequest(BaseModel):
    email: Optional[constr(strip_whitespace=True, min_length=1)] = Field(default=None, description="The new user email. If None, the user email is not changed.")  # fmt: off
    name: Optional[constr(strip_whitespace=True, min_length=1)] = Field(default=None, description="The new user name. If None, the user name is not changed.")  # fmt: off
    current_password: Optional[constr(strip_whitespace=True, min_length=1)] = Field(default=None, description="The current user password.")  # fmt: off
    password: Optional[constr(strip_whitespace=True, min_length=1)] = Field(default=None, description="The new user password. If None, the user password is not changed.")  # fmt: off
    role: Optional[int] = Field(default=None, description="The new role ID. If None, the user role is not changed.")  # fmt: off
    organization: Optional[int] = Field(default=None, description="The new organization ID. If None, the user will be removed from the organization if he was in one.")  # fmt: off
    budget: Optional[float] = Field(default=None, description="The new budget. If None, the user will have no budget.")  # fmt: off
    expires_at: Optional[int] = Field(default=None, description="The new expiration timestamp. If None, the user will never expire.")  # fmt: off

    @field_validator("expires_at", mode="before")
    def must_be_future(cls, expires_at):
        if isinstance(expires_at, int):
            if expires_at <= int(dt.datetime.now(tz=dt.UTC).timestamp()):
                raise ValueError("Wrong timestamp, must be in the future.")

        return expires_at


class UsersResponse(BaseModel):
    id: int = Field(description="The user ID.")


class UserRequest(BaseModel):
    email: constr(strip_whitespace=True, min_length=1) = Field(description="The user email.")
    name: Optional[constr(strip_whitespace=True, min_length=1)] = Field(default=None, description="The user name.")
    password: constr(strip_whitespace=True, min_length=1) = Field(description="The user password.")
    role: int = Field(description="The role ID.")
    organization: Optional[int] = Field(default=None, description="The organization ID.")
    budget: Optional[float] = Field(default=None, description="The budget.")
    expires_at: Optional[int] = Field(default=None, description="The expiration timestamp.")

    @field_validator("expires_at", mode="before")
    def must_be_future(cls, expires_at):
        if isinstance(expires_at, int):
            if expires_at <= int(dt.datetime.now(tz=dt.UTC).timestamp()):
                raise ValueError("Wrong timestamp, must be in the future.")

        return expires_at


class User(BaseModel):
    object: Literal["user"] = Field(default="user", description="The user object type.")
    id: int = Field(description="The user ID.")
    email: str = Field(description="The user email.")
    name: Optional[str] = Field(default=None, description="The user name.")
    sub: Optional[str] = Field(default=None, description="The user subject identifier. Null when using email/password auth.")
    iss: Optional[str] = Field(default=None, description="The user issuer identifier. Null when using email/password auth.")
    role: int = Field(description="The user role ID.")
    organization: Optional[int] = Field(default=None, description="The user organization ID.")
    budget: Optional[float] = Field(default=None, description="The user budget. If None, the user has unlimited budget.")
    expires_at: Optional[int] = Field(default=None, description="The user expiration timestamp. If None, the user will never expire.")
    created_at: int = Field(description="The user creation timestamp.")
    updated_at: int = Field(description="The user update timestamp.")


class Users(BaseModel):
    object: Literal["list"] = Field(default="list", description="The users list object type.")
    data: List[User] = Field(description="The users list.")
