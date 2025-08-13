import datetime as dt
from typing import List, Literal, Optional

from pydantic import Field, constr, field_validator

from app.schemas import BaseModel


class UserUpdateRequest(BaseModel):
    name: Optional[constr(strip_whitespace=True, min_length=1)] = Field(default=None, description="The new user name. If None, the user name is not changed.")  # fmt: off
    role: Optional[int] = Field(default=None, description="The new role ID. If None, the user role is not changed.")
    budget: Optional[float] = Field(default=None, description="The new budget. If None, the user will have no budget.")
    expires_at: Optional[int] = Field(default=None, description="The new expiration timestamp. If None, the user will never expire.")

    @field_validator("expires_at", mode="before")
    def must_be_future(cls, expires_at):
        if isinstance(expires_at, int):
            if expires_at <= int(dt.datetime.now(tz=dt.UTC).timestamp()):
                raise ValueError("Wrong timestamp, must be in the future.")

        return expires_at


class UsersResponse(BaseModel):
    id: int


class UserRequest(BaseModel):
    name: constr(strip_whitespace=True, min_length=1) = Field(description="The user name.")
    role: int = Field(description="The role ID.")
    budget: Optional[float] = Field(default=None, description="The budget.")
    expires_at: Optional[int] = Field(default=None, description="The expiration timestamp.")

    @field_validator("expires_at", mode="before")
    def must_be_future(cls, expires_at):
        if isinstance(expires_at, int):
            if expires_at <= int(dt.datetime.now(tz=dt.UTC).timestamp()):
                raise ValueError("Wrong timestamp, must be in the future.")

        return expires_at


class User(BaseModel):
    object: Literal["user"] = "user"
    id: int
    name: str
    role: int
    budget: Optional[float] = None
    expires_at: Optional[int] = None
    created_at: int
    updated_at: int
    email: Optional[str] = None
    sub: Optional[str] = None


class Users(BaseModel):
    object: Literal["list"] = "list"
    data: List[User]
