from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from api.domain import BaseModel
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.fastapi.schemas.admin.roles import Limit, PermissionType
from api.utils.variables import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH


class MeResponse(BaseModel):
    object: Annotated[Literal["userInfo"], Field(default="userInfo", description="The user info object type.")]
    id: Annotated[int, Field(description="The user ID.")]
    email: Annotated[str, Field(description="The user email.")]
    name: Annotated[str | None, Field(default=None, description="The user name.")]
    organization_id: Annotated[int | None, Field(default=None, description="The user organization ID.")]
    budget: Annotated[float | None, Field(default=None, description="The user budget. If None, the user has unlimited budget.")]
    permissions: Annotated[list[PermissionType], Field(description="The user permissions.")]
    limits: Annotated[list[Limit], Field(description="The user rate limits.")]
    expires: Annotated[int | None, Field(default=None, description="The user expiration timestamp. If None, the user will never expire.")]

    @model_validator(mode="before")
    @classmethod
    def from_authenticated_user(cls, data):
        if isinstance(data, AuthenticatedUserView):
            return {
                "object": "userInfo",
                "id": data.id,
                "email": data.email,
                "name": data.name,
                "organization_id": data.organization_id,
                "budget": data.budget,
                "permissions": data.permissions,
                "limits": [{"router_id": limit.router_id, "type": limit.type, "value": limit.value} for limit in data.limits],
                "expires": int(data.expires.timestamp()) if data.expires is not None else None,
            }
        return data


class UpdateMeBody(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(description="The user name.")]
    email: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=254), Field(description="The user email.")]
    current_password: Annotated[str | None, Field(default=None, min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH, description="The current user password. If None, the password is not changed and `password` is ignored.")]  # fmt: off
    password: Annotated[str | None, Field(default=None, min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH, description="The new user password. Required when `current_password` is provided. Ignored when `current_password` is None.")]  # fmt: off

    @model_validator(mode="after")
    def require_password_when_current_password_is_set(self):
        if self.current_password is not None and self.password is None:
            raise ValueError("password is required when current_password is provided.")
        return self
