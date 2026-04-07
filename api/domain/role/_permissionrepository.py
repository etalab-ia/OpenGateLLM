from abc import ABC, abstractmethod

from api.domain.role.entities import PermissionType


class PermissionRepository(ABC):
    @abstractmethod
    async def create_permissions(self, role_id: int, permissions: list[PermissionType]) -> list[PermissionType]:
        pass
