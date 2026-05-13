from pydantic import BaseModel, ConfigDict, Field

from api.domain.role.entities import Limit, PermissionType


class UserWithRoleView(BaseModel):
    model_config = ConfigDict(frozen=True)

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

    @property
    def is_admin(self) -> bool:
        return PermissionType.ADMIN in self.permissions

    def has_access_to_router(self, router_id: int) -> bool:
        if PermissionType.ADMIN in self.permissions:
            return True

        router_limits = [limit for limit in self.limits if limit.router_id == router_id]
        if len(router_limits) == 0:
            return False

        if 0 in [limit.value for limit in router_limits]:
            return False

        return True
