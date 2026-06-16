import time

from pydantic import BaseModel, ConfigDict

from api.domain.role.entities import Limit, PermissionType


class AuthenticatedUserView(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    email: str
    name: str | None
    organization: int | None
    budget: float | None
    permissions: list[PermissionType]
    limits: list[Limit]
    expires: int | None
    priority: int

    @property
    def is_admin(self) -> bool:
        return PermissionType.ADMIN in self.permissions

    @property
    def has_expired(self) -> bool:
        return self.expires is not None and self.expires < time.time()

    def cannot_access_router(self, router_id: int) -> bool:
        if PermissionType.ADMIN in self.permissions:
            return False

        router_limits = [limit for limit in self.limits if limit.router_id == router_id]
        if len(router_limits) == 0:
            return True

        if 0 in [limit.value for limit in router_limits]:
            return True

        return False
