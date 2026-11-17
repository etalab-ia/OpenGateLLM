from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from api.domain.organization import OrganizationAuthorization, OrganizationRepository
from api.domain.organization.entities import Organization
from api.domain.organization.errors import OrganizationAlreadyExistsError, UserCannotCreateOrganizationError
from api.use_cases.admin.organizations import CreateOrganizationCommand, CreateOrganizationUseCase, CreateOrganizationUseCaseSuccess


@pytest.fixture
def mock_organization_repository():
    return create_autospec(OrganizationRepository, instance=True, spec_set=True)


@pytest.fixture
def mock_organization_authorization():
    authorization = create_autospec(OrganizationAuthorization, instance=True, spec_set=True)
    authorization.can_create_organization.return_value = True
    return authorization


@pytest.fixture
def use_case(mock_organization_repository, mock_organization_authorization):
    return CreateOrganizationUseCase(organization_repository=mock_organization_repository, organization_authorization=mock_organization_authorization)


@pytest.fixture
def default_command():
    return CreateOrganizationCommand(authenticated_user_id=7, name="Acme Corp")


@pytest.fixture
def created_organization():
    return Organization(
        id=42,
        name="Acme Corp",
        users=0,
        created=datetime(2030, 1, 1, tzinfo=UTC),
        updated=datetime(2030, 1, 1, tzinfo=UTC),
    )


class TestCreateOrganizationUseCase:
    @pytest.mark.asyncio
    async def test_should_create_and_register_the_organization_when_the_user_is_allowed(
        self, use_case, mock_organization_repository, mock_organization_authorization, default_command, created_organization
    ):
        # Arrange
        mock_organization_repository.create_organization.return_value = created_organization

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, CreateOrganizationUseCaseSuccess)
        assert result.organization == created_organization
        mock_organization_authorization.can_create_organization.assert_awaited_once_with(user_id=7)
        mock_organization_repository.create_organization.assert_awaited_once_with(name="Acme Corp")
        mock_organization_authorization.register_organization.assert_awaited_once_with(organization_id=42)

    @pytest.mark.asyncio
    async def test_should_return_an_error_without_creating_anything_when_the_user_is_not_allowed(
        self, use_case, mock_organization_repository, mock_organization_authorization, default_command
    ):
        # Arrange
        mock_organization_authorization.can_create_organization.return_value = False

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert result == UserCannotCreateOrganizationError(user_id=7)
        mock_organization_repository.create_organization.assert_not_awaited()
        mock_organization_authorization.register_organization.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_the_error_without_registering_when_the_organization_already_exists(
        self, use_case, mock_organization_repository, mock_organization_authorization, default_command
    ):
        # Arrange
        mock_organization_repository.create_organization.return_value = OrganizationAlreadyExistsError(name="Acme Corp")

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert result == OrganizationAlreadyExistsError(name="Acme Corp")
        mock_organization_authorization.register_organization.assert_not_awaited()
