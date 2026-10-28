from abc import ABC, abstractmethod


class UserAuthorization(ABC):
    @abstractmethod
    async def can_create_user(self, user_id: int, organization_id: int) -> bool:
        pass

    @abstractmethod
    async def can_delete_user(self, user_id: int, target_user_id: int) -> bool:
        pass

    @abstractmethod
    async def attach_admin_to_platform(self, user_id: int) -> None:
        pass
