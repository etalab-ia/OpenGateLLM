from abc import ABC, abstractmethod

from api.domain import SortField, SortOrder
from api.domain.role.entities import Role, RolePage
from api.domain.role.errors import RoleAlreadyExistsError, RoleNotFoundError


class RoleRepository(ABC):
    @abstractmethod
    async def create_role(self, name: str) -> Role | RoleAlreadyExistsError:
        pass

    @abstractmethod
    async def get_full_role_by_id(self, role_id: int) -> Role | None:
        pass

    @abstractmethod
    async def update_role(self, role: Role) -> Role | RoleAlreadyExistsError | RoleNotFoundError:
        pass

    @abstractmethod
    async def delete_role(self, role_id: int) -> None:
        pass

    @abstractmethod
    async def get_roles_page(
        self,
        limit: int,
        offset: int,
        sort_by: SortField,
        sort_order: SortOrder,
    ) -> RolePage:
        pass
