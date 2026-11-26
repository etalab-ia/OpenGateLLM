from abc import ABC, abstractmethod


class RoleAuthorization(ABC):
    @abstractmethod
    async def can_create_role(self, user_id: int) -> bool:
        pass
