from unittest.mock import create_autospec

import pytest

from api.domain import EntitiesPage, SortOrder
from api.domain.organization import OrganizationAuthorization, OrganizationRepository
from api.domain.organization.entities import OrganizationSortField
from api.domain.organization.errors import UserCannotReadOrganizationsError
from api.tests.unit.use_case.factories import OrganizationFactory
from api.use_cases.admin.organizations import GetOrganizationsCommand, GetOrganizationsUseCase, GetOrganizationsUseCaseSuccess

AUTHENTICATED_USER_ID = 7


@pytest.fixture
def mock_organization_repository():
    return create_autospec(OrganizationRepository, instance=True, spec_set=True)


@pytest.fixture
def mock_organization_authorization():
    authorization = create_autospec(OrganizationAuthorization, instance=True, spec_set=True)
    authorization.can_read_organization.return_value = True
    return authorization


@pytest.fixture
def use_case(mock_organization_repository, mock_organization_authorization):
    return GetOrganizationsUseCase(
        organization_repository=mock_organization_repository,
        organization_authorization=mock_organization_authorization,
    )


class TestGetOrganizationsUseCase:
    @pytest.mark.asyncio
    async def test_should_return_page_with_organizations(self, use_case, mock_organization_repository, mock_organization_authorization):
        # Arrange
        organization_1 = OrganizationFactory(id=1)
        organization_2 = OrganizationFactory(id=2)
        mock_organization_repository.get_organizations_page.return_value = EntitiesPage(total=2, data=[organization_1, organization_2])
        command = GetOrganizationsCommand(
            authenticated_user_id=AUTHENTICATED_USER_ID, offset=10, limit=5, sort_by=OrganizationSortField.UPDATED, sort_order=SortOrder.DESC
        )

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, GetOrganizationsUseCaseSuccess)
        assert result.organization_page.total == 2
        assert result.organization_page.data == [organization_1, organization_2]
        mock_organization_authorization.can_read_organization.assert_awaited_once_with(user_id=AUTHENTICATED_USER_ID)
        mock_organization_repository.get_organizations_page.assert_awaited_once_with(
            name=None,
            limit=5,
            offset=10,
            sort_by=OrganizationSortField.UPDATED,
            sort_order=SortOrder.DESC,
        )

    @pytest.mark.asyncio
    async def test_should_return_user_cannot_read_organizations_error_when_user_is_not_authorized(
        self, use_case, mock_organization_repository, mock_organization_authorization
    ):
        # Arrange
        mock_organization_authorization.can_read_organization.return_value = False
        command = GetOrganizationsCommand(authenticated_user_id=AUTHENTICATED_USER_ID)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert result == UserCannotReadOrganizationsError(user_id=AUTHENTICATED_USER_ID)
        mock_organization_repository.get_organizations_page.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_empty_page_when_no_organization_matches(self, use_case, mock_organization_repository):
        # Arrange
        mock_organization_repository.get_organizations_page.return_value = EntitiesPage(total=0, data=[])
        command = GetOrganizationsCommand(authenticated_user_id=AUTHENTICATED_USER_ID)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, GetOrganizationsUseCaseSuccess)
        assert result.organization_page.total == 0
        assert result.organization_page.data == []
        mock_organization_repository.get_organizations_page.assert_awaited_once_with(
            name=None,
            limit=10,
            offset=0,
            sort_by=OrganizationSortField.ID,
            sort_order=SortOrder.ASC,
        )

    @pytest.mark.asyncio
    async def test_should_forward_name_filter_to_repository(self, use_case, mock_organization_repository):
        # Arrange
        organization = OrganizationFactory(id=1, name="Etalab")
        mock_organization_repository.get_organizations_page.return_value = EntitiesPage(total=1, data=[organization])
        command = GetOrganizationsCommand(authenticated_user_id=AUTHENTICATED_USER_ID, name="tala")

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, GetOrganizationsUseCaseSuccess)
        assert result.organization_page.data == [organization]
        mock_organization_repository.get_organizations_page.assert_awaited_once_with(
            name="tala",
            limit=10,
            offset=0,
            sort_by=OrganizationSortField.ID,
            sort_order=SortOrder.ASC,
        )
