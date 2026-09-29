from abc import ABC, abstractmethod


class OrganizationAuthorization(ABC):
    @abstractmethod
    async def can_create_organization(self, user_id: int) -> bool:
        pass

    @abstractmethod
    async def attach_organization_to_platform(self, organization_id: int) -> None:
        pass
