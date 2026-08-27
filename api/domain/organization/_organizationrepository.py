from abc import ABC, abstractmethod

from api.domain import SortOrder
from api.domain.organization.entities import Organization, OrganizationPage, OrganizationSortField
from api.domain.organization.errors import OrganizationAlreadyExistsError, OrganizationNotFoundError


class OrganizationRepository(ABC):
    @abstractmethod
    async def create_organization(self, name: str) -> Organization | OrganizationAlreadyExistsError:
        pass

    @abstractmethod
    async def get_organization_by_name(self, name: str) -> Organization | OrganizationNotFoundError:
        pass

    @abstractmethod
    async def get_organization_by_id(self, organization_id: int) -> Organization | OrganizationNotFoundError:
        pass

    @abstractmethod
    async def get_organizations_page(
        self,
        limit: int = 10,
        offset: int = 0,
        sort_by: OrganizationSortField = OrganizationSortField.ID,
        sort_order: SortOrder = SortOrder.ASC,
    ) -> OrganizationPage:
        pass

    @abstractmethod
    async def delete_organization(self, organization_id: int) -> Organization | OrganizationNotFoundError:
        pass
