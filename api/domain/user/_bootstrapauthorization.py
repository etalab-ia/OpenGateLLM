from abc import ABC, abstractmethod


class BootstrapAuthorization(ABC):
    @abstractmethod
    async def grant_platform_admin(self, user_id: int) -> None:
        pass
