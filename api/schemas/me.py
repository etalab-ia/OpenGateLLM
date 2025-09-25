import datetime as dt
from typing import List, Literal, Optional, Annotated

from pydantic import Field, constr, field_validator

from api.schemas import BaseModel
from api.schemas.admin.roles import Limit, PermissionType


class UserInfo(BaseModel):
    object: Literal["userInfo"] = Field(default="userInfo", description="The user info object type.")
    id: int = Field(description="The user ID.")
    email: str = Field(description="The user email.")
    name: Optional[str] = Field(default=None, description="The user name.")
    organization: Optional[int] = Field(default=None, description="The user organization ID.")
    budget: Optional[float] = Field(default=None, description="The user budget. If None, the user has unlimited budget.")
    permissions: List[PermissionType] = Field(description="The user permissions.")
    limits: List[Limit] = Field(description="The user rate limits.")
    expires_at: Optional[int] = Field(default=None, description="The user expiration timestamp. If None, the user will never expire.")
    created_at: int = Field(description="The user creation timestamp.")
    updated_at: int = Field(description="The user update timestamp.")
    priority: int = Field(
        default=0,
        description="The user priority (higher = higher priority). This value influences scheduling/queue priority for non-streaming model invocations.",
    )


class UpdateUserRequest(BaseModel):
    name: Optional[str] = Field(default=None, description="The user name.")
    email: Optional[str] = Field(default=None, description="The user email.")
    current_password: Optional[str] = Field(default=None, description="The current user password.")
    password: Optional[str] = Field(default=None, description="The new user password. If None, the user password is not changed.")


class CreateKeyResponse(BaseModel):
    id: int
    token: str


class CreateKey(BaseModel):
    name: Annotated[str, constr(strip_whitespace=True, min_length=1)]
    expires_at: Optional[int] = Field(None, description="Timestamp in seconds")

    @field_validator("expires_at", mode="before")
    def must_be_future(cls, expires_at):
        if isinstance(expires_at, int):
            if expires_at <= int(dt.datetime.now(tz=dt.UTC).timestamp()):
                raise ValueError("Wrong timestamp, must be in the future.")

        return expires_at


class Key(BaseModel):
    object: Literal["key"] = "key"
    id: int
    name: str
    token: str
    expires_at: Optional[int] = None
    created_at: int


class Keys(BaseModel):
    object: Literal["list"] = "list"
    data: List[Key]
