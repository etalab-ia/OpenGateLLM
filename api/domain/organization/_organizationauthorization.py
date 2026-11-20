from abc import ABC, abstractmethod


class OrganizationAuthorization(ABC):
    @abstractmethod
    async def can_read_organization(self, user_id: int) -> bool:
        pass

    @abstractmethod
    async def can_create_organization(self, user_id: int) -> bool:
        pass

    @abstractmethod
    async def can_delete_organization(self, user_id: int, organization_id: int) -> bool:
        pass

    @abstractmethod
    async def register_organization(self, organization_id: int) -> None:
        pass

    @abstractmethod
    async def unregister_organization(self, organization_id: int) -> None:
        pass
