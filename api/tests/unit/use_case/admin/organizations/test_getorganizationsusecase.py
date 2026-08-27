from unittest.mock import AsyncMock

import pytest

from api.domain import EntitiesPage, SortOrder
from api.domain.organization.entities import OrganizationSortField
from api.tests.unit.use_case.factories import OrganizationFactory
from api.use_cases.admin.organizations import GetOrganizationsCommand, GetOrganizationsUseCase, GetOrganizationsUseCaseSuccess


@pytest.fixture
def organization_repository():
    return AsyncMock()


@pytest.fixture
def use_case(organization_repository):
    return GetOrganizationsUseCase(
        organization_repository=organization_repository,
    )


class TestGetOrganizationsUseCase:
    @pytest.mark.asyncio
    async def test_should_return_page_with_organizations(self, use_case, organization_repository):
        # Arrange
        organization_1 = OrganizationFactory(id=1)
        organization_2 = OrganizationFactory(id=2)
        organization_repository.get_organizations_page.return_value = EntitiesPage(total=2, data=[organization_1, organization_2])
        command = GetOrganizationsCommand(offset=10, limit=5, sort_by=OrganizationSortField.UPDATED, sort_order=SortOrder.DESC)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, GetOrganizationsUseCaseSuccess)
        assert result.organization_page.total == 2
        assert result.organization_page.data == [organization_1, organization_2]
        organization_repository.get_organizations_page.assert_awaited_once_with(
            limit=5,
            offset=10,
            sort_by=OrganizationSortField.UPDATED,
            sort_order=SortOrder.DESC,
        )

    @pytest.mark.asyncio
    async def test_should_return_empty_page_when_no_organization_matches(self, use_case, organization_repository):
        # Arrange
        organization_repository.get_organizations_page.return_value = EntitiesPage(total=0, data=[])
        command = GetOrganizationsCommand()

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, GetOrganizationsUseCaseSuccess)
        assert result.organization_page.total == 0
        assert result.organization_page.data == []
        organization_repository.get_organizations_page.assert_awaited_once_with(
            limit=10,
            offset=0,
            sort_by=OrganizationSortField.ID,
            sort_order=SortOrder.ASC,
        )
