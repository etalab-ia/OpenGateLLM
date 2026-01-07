from abc import ABC, abstractmethod

from api.domain.router.entities import Router


class RouterRepository(ABC):
    @abstractmethod
    async def get_organization_name(self, user_id) -> str:
        pass

    @abstractmethod
    async def get_all_routers(self) -> list[Router]:
        pass
