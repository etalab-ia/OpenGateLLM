from typing import Annotated, Literal

from pydantic import Field, model_validator

from api.domain import BaseModel
from api.domain.user.views import UserInfo
from api.infrastructure.fastapi.schemas.admin.roles import Limit, PermissionType


class UserInfoResponse(BaseModel):
    object: Annotated[Literal["userInfo"], Field(default="userInfo", description="The user info object type.")]
    id: Annotated[int, Field(description="The user ID.")]
    email: Annotated[str, Field(description="The user email.")]
    name: Annotated[str | None, Field(default=None, description="The user name.")]
    organization: Annotated[int | None, Field(default=None, description="The user organization ID.")]
    budget: Annotated[float | None, Field(default=None, description="The user budget. If None, the user has unlimited budget.")]
    permissions: Annotated[list[PermissionType], Field(description="The user permissions.")]
    limits: Annotated[list[Limit], Field(description="The user rate limits.")]
    expires: Annotated[int | None, Field(default=None, description="The user expiration timestamp. If None, the user will never expire.")]
    priority: Annotated[int, Field(default=0, description="The user priority (higher = higher priority). This value influences scheduling/queue priority for non-streaming model invocations.")]  # fmt: off
    created: Annotated[int, Field(description="The user creation timestamp.")]
    updated: Annotated[int, Field(description="The user update timestamp.")]

    @model_validator(mode="before")
    @classmethod
    def from_user_info(cls, data):
        if isinstance(data, UserInfo):
            return {
                "object": "userInfo",
                "id": data.id,
                "email": data.email,
                "name": data.name,
                "organization": data.organization_id,
                "budget": data.budget,
                "permissions": [permission.value for permission in data.permissions],
                "limits": [limit.model_dump(mode="json") for limit in data.limits],
                "expires": data.expires,
                "priority": data.priority,
                "created": data.created,
                "updated": data.updated,
            }
        return data
