from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from api.domain.organization.entities import Organization
from api.domain.organization.errors import OrganizationAlreadyExistsError
from api.use_cases.admin.organizations import CreateOrganizationCommand, CreateOrganizationUseCase, CreateOrganizationUseCaseSuccess


@pytest.fixture
def organization_repository():
    return AsyncMock()


@pytest.fixture
def use_case(organization_repository):
    return CreateOrganizationUseCase(organization_repository=organization_repository)


@pytest.fixture
def default_command():
    return CreateOrganizationCommand(name="Acme Corp")


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
    async def test_should_create_organization(self, use_case, organization_repository, default_command, created_organization):
        # Arrange
        organization_repository.create_organization.return_value = created_organization

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, CreateOrganizationUseCaseSuccess)
        assert result.organization.id == 42
        assert result.organization.name == "Acme Corp"
        assert result.organization.users == 0
        organization_repository.create_organization.assert_awaited_once_with(name="Acme Corp")

    @pytest.mark.asyncio
    async def test_should_return_already_exists_error(self, use_case, organization_repository, default_command):
        # Arrange
        organization_repository.create_organization.return_value = OrganizationAlreadyExistsError(name="Acme Corp")

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, OrganizationAlreadyExistsError)
        assert result.name == "Acme Corp"
