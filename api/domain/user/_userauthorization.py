from abc import ABC, abstractmethod


class UserAuthorization(ABC):
    @abstractmethod
    async def attach_admin_to_platform(self, user_id: int) -> None:
        pass
