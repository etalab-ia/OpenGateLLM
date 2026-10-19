from typing import Annotated, Literal

from pydantic import AfterValidator, Field, StringConstraints, model_validator

from api.domain import BaseModel
from api.infrastructure.fastapi.schemas import MIN_PASSWORD_LENGTH, UnixTimestamp, reject_password_over_max_bytes
from api.infrastructure.fastapi.schemas.admin.roles import Limit, PermissionType


class MeResponse(BaseModel):
    object: Annotated[Literal["userInfo"], Field(default="userInfo", description="The user info object type.")]
    id: Annotated[int, Field(description="The user ID.")]
    email: Annotated[str, Field(description="The user email.")]
    name: Annotated[str | None, Field(default=None, description="The user name.")]
    organization_id: Annotated[int, Field(description="The user organization ID.")]
    permissions: Annotated[list[PermissionType], Field(description="The user permissions.")]
    limits: Annotated[list[Limit], Field(description="The user rate limits.")]
    expires: Annotated[UnixTimestamp | None, Field(default=None, description="The user expiration timestamp. If None, the user will never expire.")]


class UpdateMeBody(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(description="The user name.")]
    email: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=254), Field(description="The user email.")]
    current_password: Annotated[str | None, Field(default=None, min_length=MIN_PASSWORD_LENGTH, description="The current user password. If None, the password is not changed and `password` is ignored. At most 72 bytes once UTF-8 encoded."), AfterValidator(reject_password_over_max_bytes)]  # fmt: off
    password: Annotated[str | None, Field(default=None, min_length=MIN_PASSWORD_LENGTH, description="The new user password. Required when `current_password` is provided. Ignored when `current_password` is None. At most 72 bytes once UTF-8 encoded."), AfterValidator(reject_password_over_max_bytes)]  # fmt: off

    @model_validator(mode="after")
    def require_password_when_current_password_is_set(self):
        if self.current_password is not None and self.password is None:
            raise ValueError("password is required when current_password is provided.")
        return self
