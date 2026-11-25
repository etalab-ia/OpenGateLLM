from unittest.mock import create_autospec

import pytest

from api.domain.organization import OrganizationAuthorization, OrganizationRepository
from api.domain.organization.errors import OrganizationNotFoundError, UserCannotReadOrganizationError
from api.tests.unit.use_case.factories import OrganizationFactory
from api.use_cases.organizations import GetMyOrganizationCommand, GetMyOrganizationUseCase, GetMyOrganizationUseCaseSuccess


@pytest.fixture
def mock_organization_repository():
    return create_autospec(OrganizationRepository, instance=True, spec_set=True)


@pytest.fixture
def mock_organization_authorization():
    authorization = create_autospec(OrganizationAuthorization, instance=True, spec_set=True)
    authorization.can_read_my_organization.return_value = True
    return authorization


@pytest.fixture
def use_case(mock_organization_repository, mock_organization_authorization):
    return GetMyOrganizationUseCase(organization_repository=mock_organization_repository, organization_authorization=mock_organization_authorization)


class TestGetMyOrganizationUseCase:
    @pytest.mark.asyncio
    async def test_should_return_organization_when_the_user_can_read_it(
        self, use_case, mock_organization_repository, mock_organization_authorization
    ):
        # Arrange
        organization = OrganizationFactory(id=42, users=3)
        mock_organization_repository.get_organization_by_id.return_value = organization
        command = GetMyOrganizationCommand(authenticated_user_id=7, organization_id=42)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, GetMyOrganizationUseCaseSuccess)
        assert result.organization == organization
        mock_organization_authorization.can_read_my_organization.assert_awaited_once_with(user_id=7, organization_id=42)
        mock_organization_repository.get_organization_by_id.assert_awaited_once_with(organization_id=42)

    @pytest.mark.asyncio
    async def test_should_return_user_cannot_read_organization_error_without_reading_when_the_user_cannot_read_it(
        self, use_case, mock_organization_repository, mock_organization_authorization
    ):
        # Arrange
        mock_organization_authorization.can_read_my_organization.return_value = False
        command = GetMyOrganizationCommand(authenticated_user_id=7, organization_id=42)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, UserCannotReadOrganizationError)
        assert result.user_id == 7
        mock_organization_authorization.can_read_my_organization.assert_awaited_once_with(user_id=7, organization_id=42)
        mock_organization_repository.get_organization_by_id.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_organization_not_found_error_with_requested_id_when_organization_does_not_exist(
        self, use_case, mock_organization_repository, mock_organization_authorization
    ):
        # Arrange
        mock_organization_repository.get_organization_by_id.return_value = OrganizationNotFoundError()
        command = GetMyOrganizationCommand(authenticated_user_id=7, organization_id=99)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, OrganizationNotFoundError)
        assert result.id == 99
        mock_organization_authorization.can_read_my_organization.assert_awaited_once_with(user_id=7, organization_id=99)
        mock_organization_repository.get_organization_by_id.assert_awaited_once_with(organization_id=99)
