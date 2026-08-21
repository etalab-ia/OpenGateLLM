from typing import Annotated, Literal

from pydantic import Field

from api.domain import BaseModel
from api.infrastructure.fastapi.schemas.admin.roles import Limit, PermissionType


class UserInfoResponse(BaseModel):
    object: Annotated[Literal["userInfo"], Field(default="userInfo", description="The user info object type.")]
    id: Annotated[int, Field(description="The user ID.")]
    email: Annotated[str, Field(description="The user email.")]
    name: Annotated[str | None, Field(default=None, description="The user name.")]
    organization_id: Annotated[int | None, Field(default=None, description="The user organization ID.")]
    budget: Annotated[float | None, Field(default=None, description="The user budget. If None, the user has unlimited budget.")]
    permissions: Annotated[list[PermissionType], Field(description="The user permissions.")]
    limits: Annotated[list[Limit], Field(description="The user rate limits.")]
    expires: Annotated[int | None, Field(default=None, description="The user expiration timestamp. If None, the user will never expire.")]
