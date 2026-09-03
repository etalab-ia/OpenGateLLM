from unittest.mock import AsyncMock

import pytest

from api.domain.organization.errors import OrganizationHasUsersError, OrganizationNotFoundError
from api.tests.unit.use_case.factories import OrganizationFactory
from api.use_cases.admin.organizations import DeleteOrganizationCommand, DeleteOrganizationUseCase, DeleteOrganizationUseCaseSuccess


@pytest.fixture
def organization_repository():
    return AsyncMock()


@pytest.fixture
def use_case(organization_repository):
    return DeleteOrganizationUseCase(
        organization_repository=organization_repository,
    )


class TestDeleteOrganizationUseCase:
    @pytest.mark.asyncio
    async def test_should_return_deleted_organization_when_organization_exists_and_has_no_users(self, use_case, organization_repository):
        # Arrange
        organization = OrganizationFactory(id=42, users=0)

        organization_repository.get_organization_by_id.return_value = organization
        organization_repository.delete_organization.return_value = organization
        command = DeleteOrganizationCommand(organization_id=42)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, DeleteOrganizationUseCaseSuccess)
        assert result.organization == organization
        organization_repository.delete_organization.assert_awaited_once_with(organization_id=42)

    @pytest.mark.asyncio
    async def test_should_return_organization_not_found_error_when_organization_does_not_exist(self, use_case, organization_repository):
        # Arrange
        organization_repository.get_organization_by_id.return_value = OrganizationNotFoundError(id=99)
        command = DeleteOrganizationCommand(organization_id=99)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, OrganizationNotFoundError)
        assert result.id == 99
        organization_repository.delete_organization.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_organization_has_users_error_when_organization_has_users(self, use_case, organization_repository):
        # Arrange
        organization = OrganizationFactory(id=42, users=3)

        organization_repository.get_organization_by_id.return_value = organization
        command = DeleteOrganizationCommand(organization_id=42)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, OrganizationHasUsersError)
        assert result.id == 42
        organization_repository.delete_organization.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_organization_has_users_error_when_user_is_added_during_delete_race(self, use_case, organization_repository):
        # Arrange
        organization_repository.get_organization_by_id.return_value = OrganizationFactory(id=42, users=0)
        organization_repository.delete_organization.return_value = OrganizationHasUsersError(id=42)
        command = DeleteOrganizationCommand(organization_id=42)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, OrganizationHasUsersError)
        assert result.id == 42
        organization_repository.delete_organization.assert_awaited_once_with(organization_id=42)

    @pytest.mark.asyncio
    async def test_should_propagate_delete_error_when_organization_disappeared_after_the_check(self, use_case, organization_repository):
        # Arrange
        organization_repository.get_organization_by_id.return_value = OrganizationFactory(id=42, users=0)
        organization_repository.delete_organization.return_value = OrganizationNotFoundError(id=42)
        command = DeleteOrganizationCommand(organization_id=42)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, OrganizationNotFoundError)
        assert result.id == 42
