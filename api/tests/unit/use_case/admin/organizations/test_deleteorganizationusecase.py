from unittest.mock import create_autospec

import pytest

from api.domain.organization import OrganizationAuthorization, OrganizationRepository
from api.domain.organization.errors import OrganizationHasUsersError, OrganizationNotFoundError, UserCannotDeleteOrganizationError
from api.tests.unit.use_case.factories import OrganizationFactory
from api.use_cases.admin.organizations import DeleteOrganizationCommand, DeleteOrganizationUseCase, DeleteOrganizationUseCaseSuccess

AUTHENTICATED_USER_ID = 7


@pytest.fixture
def mock_organization_repository():
    return create_autospec(OrganizationRepository, instance=True, spec_set=True)


@pytest.fixture
def mock_organization_authorization():
    authorization = create_autospec(OrganizationAuthorization, instance=True, spec_set=True)
    authorization.can_delete_organization.return_value = True
    return authorization


@pytest.fixture
def use_case(mock_organization_repository, mock_organization_authorization):
    return DeleteOrganizationUseCase(
        organization_repository=mock_organization_repository,
        organization_authorization=mock_organization_authorization,
    )


class TestDeleteOrganizationUseCase:
    @pytest.mark.asyncio
    async def test_should_return_deleted_organization_when_organization_exists_and_has_no_users(
        self, use_case, mock_organization_repository, mock_organization_authorization
    ):
        # Arrange
        organization = OrganizationFactory(id=42, users=0)

        mock_organization_repository.get_organization_by_id.return_value = organization
        mock_organization_repository.delete_organization.return_value = organization
        command = DeleteOrganizationCommand(authenticated_user_id=AUTHENTICATED_USER_ID, organization_id=42)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, DeleteOrganizationUseCaseSuccess)
        assert result.organization == organization
        mock_organization_authorization.can_delete_organization.assert_awaited_once_with(user_id=AUTHENTICATED_USER_ID, organization_id=42)
        mock_organization_repository.delete_organization.assert_awaited_once_with(organization_id=42)
        mock_organization_authorization.detach_organization_from_platform.assert_awaited_once_with(organization_id=42)

    @pytest.mark.asyncio
    async def test_should_return_user_cannot_delete_organization_error_when_user_is_not_authorized(
        self, use_case, mock_organization_repository, mock_organization_authorization
    ):
        # Arrange
        mock_organization_authorization.can_delete_organization.return_value = False
        command = DeleteOrganizationCommand(authenticated_user_id=AUTHENTICATED_USER_ID, organization_id=42)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert result == UserCannotDeleteOrganizationError(user_id=AUTHENTICATED_USER_ID)
        mock_organization_repository.get_organization_by_id.assert_not_awaited()
        mock_organization_repository.delete_organization.assert_not_awaited()
        mock_organization_authorization.detach_organization_from_platform.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_organization_not_found_error_when_organization_does_not_exist(
        self, use_case, mock_organization_repository, mock_organization_authorization
    ):
        # Arrange
        mock_organization_repository.get_organization_by_id.return_value = OrganizationNotFoundError(id=99)
        command = DeleteOrganizationCommand(authenticated_user_id=AUTHENTICATED_USER_ID, organization_id=99)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, OrganizationNotFoundError)
        assert result.id == 99
        mock_organization_repository.delete_organization.assert_not_awaited()
        mock_organization_authorization.detach_organization_from_platform.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_organization_has_users_error_when_organization_has_users(
        self, use_case, mock_organization_repository, mock_organization_authorization
    ):
        # Arrange
        mock_organization_repository.get_organization_by_id.return_value = OrganizationFactory(id=42, users=3)
        command = DeleteOrganizationCommand(authenticated_user_id=AUTHENTICATED_USER_ID, organization_id=42)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, OrganizationHasUsersError)
        assert result.id == 42
        mock_organization_repository.delete_organization.assert_not_awaited()
        mock_organization_authorization.detach_organization_from_platform.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_organization_has_users_error_when_user_is_added_during_delete_race(
        self, use_case, mock_organization_repository, mock_organization_authorization
    ):
        # Arrange
        mock_organization_repository.get_organization_by_id.return_value = OrganizationFactory(id=42, users=0)
        mock_organization_repository.delete_organization.return_value = OrganizationHasUsersError(id=42)
        command = DeleteOrganizationCommand(authenticated_user_id=AUTHENTICATED_USER_ID, organization_id=42)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, OrganizationHasUsersError)
        assert result.id == 42
        mock_organization_repository.delete_organization.assert_awaited_once_with(organization_id=42)
        mock_organization_authorization.detach_organization_from_platform.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_propagate_delete_error_when_organization_disappeared_after_the_check(self, use_case, mock_organization_repository):
        # Arrange
        mock_organization_repository.get_organization_by_id.return_value = OrganizationFactory(id=42, users=0)
        mock_organization_repository.delete_organization.return_value = OrganizationNotFoundError(id=42)
        command = DeleteOrganizationCommand(authenticated_user_id=AUTHENTICATED_USER_ID, organization_id=42)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, OrganizationNotFoundError)
        assert result.id == 42
