from unittest.mock import AsyncMock

import pytest

from api.domain.organization.errors import OrganizationNotFoundError
from api.tests.unit.use_case.factories import OrganizationFactory
from api.use_cases.admin.organizations import GetOneOrganizationCommand, GetOneOrganizationUseCase, GetOneOrganizationUseCaseSuccess


@pytest.fixture
def organization_repository():
    return AsyncMock()


@pytest.fixture
def use_case(organization_repository):
    return GetOneOrganizationUseCase(
        organization_repository=organization_repository,
    )


class TestGetOneOrganizationUseCase:
    @pytest.mark.asyncio
    async def test_should_return_organization_when_it_exists(self, use_case, organization_repository):
        # Arrange
        organization = OrganizationFactory(id=42, users=3)
        organization_repository.get_organization_by_id.return_value = organization
        command = GetOneOrganizationCommand(organization_id=42)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, GetOneOrganizationUseCaseSuccess)
        assert result.organization == organization
        organization_repository.get_organization_by_id.assert_awaited_once_with(organization_id=42)

    @pytest.mark.asyncio
    async def test_should_return_organization_not_found_error_with_requested_id_when_organization_does_not_exist(
        self, use_case, organization_repository
    ):
        # Arrange
        organization_repository.get_organization_by_id.return_value = OrganizationNotFoundError()
        command = GetOneOrganizationCommand(organization_id=99)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, OrganizationNotFoundError)
        assert result.id == 99
        organization_repository.get_organization_by_id.assert_awaited_once_with(organization_id=99)
