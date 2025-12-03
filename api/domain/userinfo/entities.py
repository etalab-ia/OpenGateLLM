from pydantic import BaseModel, Field

from api.domain.role.entities import Limit, PermissionType


class UserInfo(BaseModel):
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
