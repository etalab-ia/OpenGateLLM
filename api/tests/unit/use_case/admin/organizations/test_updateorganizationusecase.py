from unittest.mock import AsyncMock

import pytest

from api.domain.organization.errors import OrganizationAlreadyExistsError, OrganizationNotFoundError
from api.tests.unit.use_case.factories import OrganizationFactory
from api.use_cases.admin.organizations import UpdateOrganizationCommand, UpdateOrganizationUseCase, UpdateOrganizationUseCaseSuccess


@pytest.fixture
def organization_repository():
    return AsyncMock()


@pytest.fixture
def use_case(organization_repository):
    return UpdateOrganizationUseCase(
        organization_repository=organization_repository,
    )


class TestUpdateOrganizationUseCase:
    @pytest.mark.asyncio
    async def test_should_return_renamed_organization_when_organization_exists(self, use_case, organization_repository):
        # Arrange
        organization = OrganizationFactory(id=42, name="old-name")
        renamed_organization = organization.with_name("new-name")

        organization_repository.get_organization_by_id.return_value = organization
        organization_repository.update_organization.return_value = renamed_organization
        command = UpdateOrganizationCommand(organization_id=42, name="new-name")

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, UpdateOrganizationUseCaseSuccess)
        assert result.organization == renamed_organization
        organization_repository.update_organization.assert_awaited_once_with(organization=renamed_organization)

    @pytest.mark.asyncio
    async def test_should_return_organization_not_found_error_when_organization_does_not_exist(self, use_case, organization_repository):
        # Arrange
        organization_repository.get_organization_by_id.return_value = OrganizationNotFoundError()
        command = UpdateOrganizationCommand(organization_id=99, name="new-name")

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, OrganizationNotFoundError)
        assert result.id == 99
        organization_repository.update_organization.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_organization_already_exists_error_when_name_is_taken(self, use_case, organization_repository):
        # Arrange
        organization = OrganizationFactory(id=42, name="old-name")

        organization_repository.get_organization_by_id.return_value = organization
        organization_repository.update_organization.return_value = OrganizationAlreadyExistsError(name="new-name")
        command = UpdateOrganizationCommand(organization_id=42, name="new-name")

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, OrganizationAlreadyExistsError)
        assert result.name == "new-name"

    @pytest.mark.asyncio
    async def test_should_not_update_organization_when_name_is_unchanged(self, use_case, organization_repository):
        # Arrange
        organization = OrganizationFactory(id=42, name="same-name")

        organization_repository.get_organization_by_id.return_value = organization
        command = UpdateOrganizationCommand(organization_id=42, name="same-name")

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, UpdateOrganizationUseCaseSuccess)
        assert result.organization == organization
        organization_repository.update_organization.assert_not_awaited()
