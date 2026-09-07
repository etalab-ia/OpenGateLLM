from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import ConfigDict, Field, StringConstraints, field_validator

from api.domain import BaseModel
from api.infrastructure.fastapi.schemas import UnixTimestamp
from api.utils.variables import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH


class CreateUserBody(BaseModel):
    email: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=254), Field(..., description="The user email.")]
    name: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1), Field(default=None, description="The user name.")]
    password: Annotated[str, StringConstraints(strip_whitespace=True, min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH), Field(description="The user password.")]  # fmt: off
    role_id: Annotated[int, Field(..., description="The role ID.")]
    organization_id: Annotated[int | None, Field(default=None, description="The organization ID.")]
    budget: Annotated[float | None, Field(default=None, description="The budget.")]
    expires: Annotated[int | None, Field(default=None, description="The expiration timestamp.")]
    priority: Annotated[int, Field(default=0, ge=0, description="The user priority. Higher value means higher priority.")]

    @field_validator("expires", mode="after")
    def convert_expires_to_datetime(cls, expires) -> None | datetime:
        if expires is None:
            return expires
        return datetime.fromtimestamp(timestamp=expires, tz=UTC)


class UserResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    object: Annotated[Literal["user"], Field("user", description="Type of the object.")]
    id: Annotated[int, Field(..., description="ID of the user.")]
    email: Annotated[str, Field(..., description="Email of the user.")]
    name: Annotated[str | None, Field(default=None, description="Name of the user.")]
    sub: Annotated[str | None, Field(default=None, description="Subject identifier for SSO.")]
    iss: Annotated[str | None, Field(default=None, description="Issuer identifier for SSO.")]
    role_id: Annotated[int, Field(..., description="ID of the role assigned to the user.")]
    organization_id: Annotated[int | None, Field(default=None, description="ID of the organization the user belongs to.")]
    budget: Annotated[float | None, Field(default=None, description="Budget allocated to the user.")]
    expires: Annotated[UnixTimestamp | None, Field(default=None, description="Expiration time of the user, as Unix timestamp.")]
    created: Annotated[UnixTimestamp, Field(..., description="Time of creation, as Unix timestamp.")]
    updated: Annotated[UnixTimestamp, Field(..., description="Time of last update, as Unix timestamp.")]
    priority: Annotated[int, Field(..., description="Priority of the user. Higher value means higher priority.")]


class UsersResponse(BaseModel):
    object: Annotated[Literal["list"], Field("list", description="Type of the object.")]
    total: Annotated[int, Field(..., description="Total number of users matching the query.")]
    offset: Annotated[int, Field(..., description="Number of users skipped.")]
    limit: Annotated[int, Field(..., description="Maximum number of users returned.")]
    data: Annotated[list[UserResponse], Field(..., description="List of users.")]


class UserUpdateRequest(BaseModel):
    email: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=254), Field(..., description="The new user email.")]
    name: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1), Field(..., description="The new user name. If null, the user name is removed.")]  # fmt: off
    current_password: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH), Field(default=None, description="The current user password. Only required to change the password.")]  # fmt: off
    password: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH), Field(default=None, description="The new user password. If omitted, the user password is not changed.")]  # fmt: off
    role_id: Annotated[int, Field(..., description="The new role ID.")]
    organization_id: Annotated[int | None, Field(..., description="The new organization ID. If null, the user is removed from the organization if he was in one.")]  # fmt: off
    budget: Annotated[float | None, Field(..., description="The new budget. If null, the user will have no budget.")]
    expires: Annotated[int | None, Field(..., description="The new expiration timestamp. If null, the user will never expire.")]
    priority: Annotated[int, Field(..., ge=0, description="The new user priority. Higher value means higher priority.")]

    @field_validator("expires", mode="after")
    def convert_expires_to_datetime(cls, expires) -> None | datetime:
        if expires is None:
            return expires
        return datetime.fromtimestamp(timestamp=expires, tz=UTC)
