from abc import ABC, abstractmethod

from api.domain.role.entities import Role
from api.domain.role.errors import RoleAlreadyExistsError


class RoleRepository(ABC):
    @abstractmethod
    async def create_role(self, name: str) -> Role | RoleAlreadyExistsError:
        pass

    @abstractmethod
    async def get_roles(self, role_id: str) -> list[Role]:
        pass

    @abstractmethod
    async def update_role(self, role: Role) -> Role:
        pass

    @abstractmethod
    async def delete_role(self, role_id: str) -> None:
        pass
