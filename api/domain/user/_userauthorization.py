from abc import ABC, abstractmethod


class UserAuthorization(ABC):
    @abstractmethod
    async def can_create_user(self, user_id: int, organization_id: int) -> bool:
        pass

    @abstractmethod
    async def can_delete_user(self, user_id: int, target_user_id: int) -> bool:
        pass

    @abstractmethod
    async def can_read_users(self, user_id: int) -> bool:
        pass

    @abstractmethod
    async def grant_platform_admin(self, user_id: int) -> None:
        pass

    @abstractmethod
    async def revoke_platform_admin(self, user_id: int) -> None:
        pass
