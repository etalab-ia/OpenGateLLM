import datetime as dt
from typing import Annotated, Literal

from pydantic import Field, constr, field_validator

from api.schemas import BaseModel
from api.schemas.admin.roles import Limit, PermissionType


class UserInfo(BaseModel):
    object: Literal["userInfo"] = Field(default="userInfo", description="The user info object type.")
    id: int = Field(description="The user ID.")
    email: str = Field(description="The user email.")
    name: str | None = Field(default=None, description="The user name.")
    organization: int | None = Field(default=None, description="The user organization ID.")
    budget: float | None = Field(default=None, description="The user budget. If None, the user has unlimited budget.")
    permissions: list[PermissionType] = Field(description="The user permissions.")
    limits: list[Limit] = Field(description="The user rate limits.")
    expires: int | None = Field(default=None, description="The user expiration timestamp. If None, the user will never expire.")
    priority: int = Field(default=0,description="The user priority (higher = higher priority). This value influences scheduling/queue priority for non-streaming model invocations.")  # fmt: off
    created: int = Field(description="The user creation timestamp.")
    updated: int = Field(description="The user update timestamp.")


class UpdateUserRequest(BaseModel):
    name: str | None = Field(default=None, description="The user name.")
    email: str | None = Field(default=None, description="The user email.")
    current_password: str | None = Field(default=None, description="The current user password.")
    password: str | None = Field(default=None, description="The new user password. If None, the user password is not changed.")


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
