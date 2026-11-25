from abc import ABC, abstractmethod


class RouterAuthorization(ABC):
    @abstractmethod
    async def can_create_router(self, user_id: int) -> bool:
        pass
