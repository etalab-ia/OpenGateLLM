from abc import ABC, abstractmethod

from api.domain.role import Role


class RoleRepository(ABC):
    @abstractmethod
    def get_roles(self, role_id: str) -> list[Role]:
        pass