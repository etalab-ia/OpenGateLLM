from abc import ABC, abstractmethod


class RouterAuthorization(ABC):
    @abstractmethod
    async def can_create_router(self, user_id: int) -> bool:
        pass

    @abstractmethod
    async def can_delete_router(self, user_id: int, router_id: int) -> bool:
        pass

    @abstractmethod
    async def can_read_router(self, user_id: int) -> bool:
        pass

    @abstractmethod
    async def can_update_router(self, user_id: int, router_id: int) -> bool:
        pass
