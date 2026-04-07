from unittest.mock import AsyncMock

import pytest

from api.domain.role.entities import PermissionType
from api.domain.role.errors import RoleAlreadyExistsError
from api.domain.user.errors import UserAlreadyExistsError
from api.tests.unit.use_case.factories import RoleFactory, UserFactory
from api.use_cases.admin.bootstrapadminusecase import (
    BootstrapAdminCommand,
    BootstrapAdminUseCase,
    BootstrapAdminUseCaseSkipped,
    BootstrapAdminUseCaseSuccess,
)


@pytest.fixture
def user_repository():
    return AsyncMock()


@pytest.fixture
def role_repository():
    return AsyncMock()


@pytest.fixture
def permission_repository():
    return AsyncMock()


@pytest.fixture
def limit_repository():
    return AsyncMock()


@pytest.fixture
def use_case(user_repository, role_repository, permission_repository, limit_repository):
    return BootstrapAdminUseCase(
        user_repository=user_repository,
        role_repository=role_repository,
        limit_repository=limit_repository,
        permission_repository=permission_repository,
    )


@pytest.fixture
def command():
    return BootstrapAdminCommand(
        name="admin",
        email="admin@opengatellm.org",
        password="s3cr3t",
        permissions=[PermissionType.ADMIN],
        limits=[],
    )


class TestBootstrapAdminUserUseCase:
    @pytest.mark.asyncio
    async def test_happy_path_returns_success_instance(self, use_case, user_repository, role_repository, command):
        # Arrange
        role = RoleFactory(id=42)
        user = UserFactory(id=10, email="admin@opengatellm.org")
        user_repository.has_admin_user.return_value = False
        role_repository.create_role.return_value = role
        user_repository.create_user.return_value = user

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, BootstrapAdminUseCaseSuccess)

        assert result.email == "admin@opengatellm.org"
        assert result.user_id == 10
        assert result.role_id == 42

        user_repository.create_user.assert_awaited_once_with(email=command.email, password=command.password, role_id=role.id, name=command.name)

    @pytest.mark.asyncio
    async def test_skips_when_admin_user_already_exists(self, use_case, user_repository, role_repository, command):
        # Arrange
        user_repository.has_admin_user.return_value = True

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, BootstrapAdminUseCaseSkipped)
        assert result.email == "admin@opengatellm.org"
        assert result.name == "admin"
        role_repository.create_role.assert_not_awaited()
        user_repository.create_user.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_returns_role_already_exists_error_when_role_name_conflicts(self, use_case, user_repository, role_repository, command):
        # Arrange
        user_repository.has_admin_user.return_value = False
        role_repository.create_role.return_value = RoleAlreadyExistsError(name="admin")

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, RoleAlreadyExistsError)
        assert result.name == "admin"

    @pytest.mark.asyncio
    async def test_should_return_user_already_exists_error_when_email_conflicts_and_has_no_admin(
        self, use_case, user_repository, role_repository, command
    ):
        # Arrange
        user_repository.has_admin_user.return_value = False
        role_repository.create_role.return_value = RoleFactory()
        user_repository.create_user.return_value = UserAlreadyExistsError(email="admin@opengatellm.org")

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, UserAlreadyExistsError)
        assert result.email == "admin@opengatellm.org"
