from abc import ABC, abstractmethod

from api.domain.role.entities import Limit


class LimitRepository(ABC):
    @abstractmethod
    async def create_limits(self, role_id: int, limits: list[Limit]) -> list[Limit]:
        pass

    @abstractmethod
    async def delete_limits_by_role_id(
        self,
        role_id: int,
    ) -> list[Limit]:
        pass

    @abstractmethod
    async def get_limits_by_role_ids(
        self,
        role_ids: list[int],
    ) -> dict[int, list[Limit]]:
        pass
