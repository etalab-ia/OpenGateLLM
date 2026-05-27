import datetime as dt
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_validator

from api.infrastructure.fastapi.schemas import BaseModel


class CreateUserBody(BaseModel):
    email: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=254), Field(..., description="The user email.")]
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = Field(default=None, description="The user name.")
    password: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=72)] = Field(..., description="The user password.")
    role: int = Field(..., description="The role ID.")
    organization: int | None = Field(default=None, description="The organization ID.")
    budget: float | None = Field(default=None, description="The budget.")
    expires: int | None = Field(default=None, description="The expiration timestamp.")
    priority: int = Field(default=0, ge=0, description="The user priority. Higher value means higher priority.")

    @field_validator("expires", mode="before")
    def must_be_future(cls, expires):
        if isinstance(expires, int):
            if expires <= int(dt.datetime.now(tz=dt.UTC).timestamp()):
                raise ValueError("Wrong timestamp, must be in the future.")
        return expires


class UserResponse(BaseModel):
    object: Annotated[Literal["user"], Field("user", description="Type of the object.")]
    id: Annotated[int, Field(..., description="ID of the user.")]
    email: Annotated[str, Field(..., description="Email of the user.")]
    name: Annotated[str | None, Field(default=None, description="Name of the user.")]
    sub: Annotated[str | None, Field(default=None, description="Subject identifier for SSO.")]
    iss: Annotated[str | None, Field(default=None, description="Issuer identifier for SSO.")]
    role: Annotated[int, Field(..., description="ID of the role assigned to the user.")]
    organization: Annotated[int | None, Field(default=None, description="ID of the organization the user belongs to.")]
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
