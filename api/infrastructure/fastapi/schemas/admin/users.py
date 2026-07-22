import datetime as dt
from typing import Annotated, Literal

from pydantic import AfterValidator, ConfigDict, Field, StringConstraints

from api.infrastructure.fastapi.schemas import BaseModel


def _must_be_future(expires: int) -> int:
    if expires <= int(dt.datetime.now(tz=dt.UTC).timestamp()):
        raise ValueError("Wrong timestamp, must be in the future.")
    return expires


FutureTimestamp = Annotated[int, AfterValidator(_must_be_future)]


class CreateUserBody(BaseModel):
    email: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=254), Field(..., description="The user email.")]
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = Field(default=None, description="The user name.")
    password: Annotated[Annotated[str, StringConstraints(strip_whitespace=True, min_length=6, max_length=72)], Field(description="The user password.")]  # fmt: off
    role: int = Field(..., description="The role ID.")
    organization_id: int | None = Field(default=None, description="The organization ID.")
    budget: float | None = Field(default=None, description="The budget.")
    expires: FutureTimestamp | None = Field(default=None, description="The expiration timestamp.")
    priority: int = Field(default=0, ge=0, description="The user priority. Higher value means higher priority.")


class UserResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    object: Annotated[Literal["user"], Field("user", description="Type of the object.")]
    id: Annotated[int, Field(..., description="ID of the user.")]
    email: Annotated[str, Field(..., description="Email of the user.")]
    name: Annotated[str | None, Field(default=None, description="Name of the user.")]
    sub: Annotated[str | None, Field(default=None, description="Subject identifier for SSO.")]
    iss: Annotated[str | None, Field(default=None, description="Issuer identifier for SSO.")]
    role: Annotated[int, Field(..., description="ID of the role assigned to the user.")]
    organization_id: Annotated[int | None, Field(default=None, description="ID of the organization the user belongs to.")]
    budget: Annotated[float | None, Field(default=None, description="Budget allocated to the user.")]
    expires: Annotated[int | None, Field(default=None, description="Expiration time of the user, as Unix timestamp.")]
    created: Annotated[int, Field(..., description="Time of creation, as Unix timestamp.")]
    updated: Annotated[int, Field(..., description="Time of last update, as Unix timestamp.")]
    priority: Annotated[int, Field(..., description="Priority of the user. Higher value means higher priority.")]


class UsersResponse(BaseModel):
    object: Annotated[Literal["list"], Field("list", description="Type of the object.")]
    total: Annotated[int, Field(..., description="Total number of users matching the query.")]
    offset: Annotated[int, Field(..., description="Number of users skipped.")]
    limit: Annotated[int, Field(..., description="Maximum number of users returned.")]
    data: Annotated[list[UserResponse], Field(..., description="List of users.")]


class UserUpdateRequest(BaseModel):
    email: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=254)] | None = Field(default=None, description="The new user email. If None, the user email is not changed.")  # fmt: off
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = Field(default=None, description="The new user name. If None, the user name is not changed.")  # fmt: off
    current_password: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=72)] | None = Field(default=None, description="The current user password.")  # fmt: off
    password: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=72)] | None = Field(default=None, description="The new user password. If None, the user password is not changed.")  # fmt: off
    role: int | None = Field(default=None, description="The new role ID. If None, the user role is not changed.")  # fmt: off
    organization: int | None = Field(default=None, description="The new organization ID. If None, the user will be removed from the organization if he was in one.")  # fmt: off
    budget: float | None = Field(default=None, description="The new budget. If None, the user will have no budget.")  # fmt: off
    expires: FutureTimestamp | None = Field(default=None, description="The new expiration timestamp. If None, the user will never expire.")  # fmt: off
    priority: int | None = Field(default=None, ge=0, description="The new user priority. Higher value means higher priority. If None, unchanged.")  # fmt: off
