from abc import ABC, abstractmethod

from api.domain.role.entities import Role
from api.domain.role.errors import RoleAlreadyExistsError, RoleNotFoundError


class RoleRepository(ABC):
    @abstractmethod
    async def create_role(self, name: str) -> Role | RoleAlreadyExistsError:
        pass

    @abstractmethod
    async def get_roles(self, role_id: str) -> list[Role]:
        pass

    @abstractmethod
    async def get_role_by_id(self, role_id: int) -> Role | RoleNotFoundError:
        pass

    @abstractmethod
    async def update_role(self, role: Role) -> Role | RoleAlreadyExistsError | RoleNotFoundError:
        pass

    @abstractmethod
    async def delete_role(self, role_id: str) -> None:
        pass
