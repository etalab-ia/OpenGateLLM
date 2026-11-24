from unittest.mock import create_autospec

import pytest

from api.domain.organization import OrganizationAuthorization, OrganizationRepository
from api.domain.organization.errors import OrganizationAlreadyExistsError, OrganizationNotFoundError, UserCannotUpdateOrganizationError
from api.tests.unit.use_case.factories import OrganizationFactory
from api.use_cases.admin.organizations import UpdateOrganizationCommand, UpdateOrganizationUseCase, UpdateOrganizationUseCaseSuccess

AUTHENTICATED_USER_ID = 7


@pytest.fixture
def mock_organization_repository():
    return create_autospec(OrganizationRepository, instance=True, spec_set=True)


@pytest.fixture
def mock_organization_authorization():
    authorization = create_autospec(OrganizationAuthorization, instance=True, spec_set=True)
    authorization.can_update_organization.return_value = True
    return authorization


@pytest.fixture
def use_case(mock_organization_repository, mock_organization_authorization):
    return UpdateOrganizationUseCase(
        organization_repository=mock_organization_repository,
        organization_authorization=mock_organization_authorization,
    )


class TestUpdateOrganizationUseCase:
    @pytest.mark.asyncio
    async def test_should_return_renamed_organization_when_organization_exists(
        self, use_case, mock_organization_repository, mock_organization_authorization
    ):
        # Arrange
        organization = OrganizationFactory(id=42, name="old-name")
        renamed_organization = organization.with_name("new-name")

        mock_organization_repository.get_organization_by_id.return_value = organization
        mock_organization_repository.update_organization.return_value = renamed_organization
        command = UpdateOrganizationCommand(authenticated_user_id=AUTHENTICATED_USER_ID, organization_id=42, name="new-name")

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, UpdateOrganizationUseCaseSuccess)
        assert result.organization == renamed_organization
        mock_organization_authorization.can_update_organization.assert_awaited_once_with(user_id=AUTHENTICATED_USER_ID, organization_id=42)
        mock_organization_repository.update_organization.assert_awaited_once_with(organization=renamed_organization)

    @pytest.mark.asyncio
    async def test_should_return_user_cannot_update_organization_error_when_user_is_not_authorized(
        self, use_case, mock_organization_repository, mock_organization_authorization
    ):
        # Arrange
        mock_organization_authorization.can_update_organization.return_value = False
        command = UpdateOrganizationCommand(authenticated_user_id=AUTHENTICATED_USER_ID, organization_id=42, name="new-name")

        # Act
        result = await use_case.execute(command)

        # Assert
        assert result == UserCannotUpdateOrganizationError(user_id=AUTHENTICATED_USER_ID)
        mock_organization_repository.get_organization_by_id.assert_not_awaited()
        mock_organization_repository.update_organization.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_organization_not_found_error_when_organization_does_not_exist(
        self, use_case, mock_organization_repository, mock_organization_authorization
    ):
        # Arrange
        mock_organization_repository.get_organization_by_id.return_value = OrganizationNotFoundError()
        command = UpdateOrganizationCommand(authenticated_user_id=AUTHENTICATED_USER_ID, organization_id=99, name="new-name")

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, OrganizationNotFoundError)
        assert result.id == 99
        mock_organization_repository.update_organization.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_organization_already_exists_error_when_name_is_taken(
        self, use_case, mock_organization_repository, mock_organization_authorization
    ):
        # Arrange
        organization = OrganizationFactory(id=42, name="old-name")

        mock_organization_repository.get_organization_by_id.return_value = organization
        mock_organization_repository.update_organization.return_value = OrganizationAlreadyExistsError(name="new-name")
        command = UpdateOrganizationCommand(authenticated_user_id=AUTHENTICATED_USER_ID, organization_id=42, name="new-name")

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, OrganizationAlreadyExistsError)
        assert result.name == "new-name"

    @pytest.mark.asyncio
    async def test_should_not_update_organization_when_name_is_unchanged(
        self, use_case, mock_organization_repository, mock_organization_authorization
    ):
        # Arrange
        organization = OrganizationFactory(id=42, name="same-name")

        mock_organization_repository.get_organization_by_id.return_value = organization
        command = UpdateOrganizationCommand(authenticated_user_id=AUTHENTICATED_USER_ID, organization_id=42, name="same-name")

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, UpdateOrganizationUseCaseSuccess)
        assert result.organization == organization
        mock_organization_repository.update_organization.assert_not_awaited()
