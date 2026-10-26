from abc import ABC, abstractmethod


class UserAuthorization(ABC):
    @abstractmethod
    async def grant_platform_admin(self, user_id: int) -> None:
        pass
