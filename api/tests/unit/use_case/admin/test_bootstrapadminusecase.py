from unittest.mock import AsyncMock, MagicMock

import pytest

from api.domain.role.entities import PermissionType
from api.domain.role.errors import RoleAlreadyExistsError, RoleNotFoundError
from api.domain.user.errors import UserAlreadyExistsError, UserNotFoundError
from api.tests.unit.use_case.factories import RoleFactory, UserFactory
from api.use_cases.admin import BootstrapAdminCommand, BootstrapAdminUseCase, BootstrapAdminUseCaseSkipped, BootstrapAdminUseCaseSuccess


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
def user_password_encoder():
    encoder = MagicMock()
    encoder.encode_password.return_value = "$2b$12$encodedpasswordhash"
    return encoder


@pytest.fixture
def use_case(user_repository, role_repository, permission_repository, limit_repository, user_password_encoder):
    return BootstrapAdminUseCase(
        user_repository=user_repository,
        role_repository=role_repository,
        limit_repository=limit_repository,
        permission_repository=permission_repository,
        user_password_encoder=user_password_encoder,
    )


@pytest.fixture
def command():
    return BootstrapAdminCommand(email="admin@opengatellm.org", password="s3cr3t")


class TestBootstrapAdminUserUseCase:
    @pytest.mark.asyncio
    async def test_successfully_creates_admin_user_and_role(
        self, use_case, user_repository, role_repository, permission_repository, user_password_encoder, command
    ):
        # Arrange
        role = RoleFactory(id=42, permissions=[])
        user = UserFactory(id=10, email="admin@opengatellm.org", role_id=42)
        user_repository.get_first_admin_user.return_value = UserNotFoundError()
        role_repository.get_role_with_permissions_and_limits_by_name.return_value = RoleNotFoundError(
            name=BootstrapAdminUseCase.BOOTSTRAP_ADMIN_ROLE_NAME
        )
        role_repository.create_role.return_value = role
        user_repository.get_user_by_email.return_value = UserNotFoundError(email=command.email)
        user_repository.create_user.return_value = user

        # Act
        result = await use_case.execute(command)

        # Assert
        assert result == BootstrapAdminUseCaseSuccess(user_id=10, email="admin@opengatellm.org", role_id=42)

        role_repository.create_role.assert_awaited_once_with(name=BootstrapAdminUseCase.BOOTSTRAP_ADMIN_ROLE_NAME)
        permission_repository.create_permissions.assert_awaited_once_with(role_id=42, permissions=[PermissionType.ADMIN])
        user_password_encoder.encode_password.assert_called_once_with(password=command.password)
        user_repository.create_user.assert_awaited_once_with(
            email=command.email,
            password="$2b$12$encodedpasswordhash",
            role_id=42,
            name=BootstrapAdminUseCase.BOOTSTRAP_ADMIN_USER_NAME,
        )

    @pytest.mark.asyncio
    async def test_skips_when_admin_user_already_exists(self, use_case, user_repository, role_repository, command):
        # Arrange
        existing_user = UserFactory(id=7, email="admin@opengatellm.org", role_id=99)
        user_repository.get_first_admin_user.return_value = existing_user

        # Act
        result = await use_case.execute(command)

        # Assert
        assert result == BootstrapAdminUseCaseSkipped(user_id=7, email="admin@opengatellm.org", role_id=99)
        role_repository.get_role_with_permissions_and_limits_by_name.assert_not_awaited()
        role_repository.create_role.assert_not_awaited()
        user_repository.create_user.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_reuses_existing_role_when_role_name_conflicts(
        self, use_case, user_repository, role_repository, permission_repository, user_password_encoder, command
    ):
        # Arrange
        existing_role = RoleFactory(
            id=5,
            name=BootstrapAdminUseCase.BOOTSTRAP_ADMIN_ROLE_NAME,
            permissions=[PermissionType.ADMIN],
        )
        user = UserFactory(id=11, email="admin@opengatellm.org", role_id=5)
        user_repository.get_first_admin_user.return_value = UserNotFoundError()
        role_repository.get_role_with_permissions_and_limits_by_name.return_value = existing_role
        user_repository.get_user_by_email.return_value = UserNotFoundError(email=command.email)
        user_repository.create_user.return_value = user

        # Act
        result = await use_case.execute(command)

        # Assert
        assert result == BootstrapAdminUseCaseSuccess(user_id=11, email="admin@opengatellm.org", role_id=5)
        role_repository.create_role.assert_not_awaited()
        permission_repository.create_permissions.assert_not_awaited()
        user_password_encoder.encode_password.assert_called_once_with(password=command.password)
        user_repository.create_user.assert_awaited_once_with(
            email=command.email,
            password="$2b$12$encodedpasswordhash",
            role_id=5,
            name=BootstrapAdminUseCase.BOOTSTRAP_ADMIN_USER_NAME,
        )

    @pytest.mark.asyncio
    async def test_updates_existing_user_when_email_conflicts_and_has_no_admin(self, use_case, user_repository, role_repository, command):
        # Arrange
        role = RoleFactory(id=3, permissions=[])
        existing_user = UserFactory(id=20, email="admin@opengatellm.org", role_id=1)
        updated_user = existing_user.model_copy(update={"role_id": 3})
        user_repository.get_first_admin_user.return_value = UserNotFoundError()
        role_repository.get_role_with_permissions_and_limits_by_name.return_value = RoleNotFoundError(
            name=BootstrapAdminUseCase.BOOTSTRAP_ADMIN_ROLE_NAME
        )
        role_repository.create_role.return_value = role
        user_repository.get_user_by_email.return_value = existing_user

        # Act
        result = await use_case.execute(command)

        # Assert
        assert result == BootstrapAdminUseCaseSuccess(user_id=20, email="admin@opengatellm.org", role_id=3)
        user_repository.create_user.assert_not_awaited()
        user_repository.update_user.assert_awaited_once()
        assert user_repository.update_user.await_args.kwargs["user"] == updated_user

    @pytest.mark.asyncio
    async def test_should_reuse_the_role_created_by_a_concurrent_worker_when_create_role_conflicts(
        self, use_case, user_repository, role_repository, permission_repository, command
    ):
        # Arrange: another worker inserted the role between our read and our insert
        concurrent_role = RoleFactory(id=5, name=BootstrapAdminUseCase.BOOTSTRAP_ADMIN_ROLE_NAME, permissions=[PermissionType.ADMIN])
        user = UserFactory(id=11, email="admin@opengatellm.org", role_id=5)
        user_repository.get_first_admin_user.return_value = UserNotFoundError()
        role_repository.get_role_with_permissions_and_limits_by_name.side_effect = [
            RoleNotFoundError(name=BootstrapAdminUseCase.BOOTSTRAP_ADMIN_ROLE_NAME),
            concurrent_role,
        ]
        role_repository.create_role.return_value = RoleAlreadyExistsError(name=BootstrapAdminUseCase.BOOTSTRAP_ADMIN_ROLE_NAME)
        user_repository.get_user_by_email.return_value = UserNotFoundError(email=command.email)
        user_repository.create_user.return_value = user

        # Act
        result = await use_case.execute(command)

        # Assert
        assert result == BootstrapAdminUseCaseSuccess(user_id=11, email="admin@opengatellm.org", role_id=5)
        assert role_repository.get_role_with_permissions_and_limits_by_name.await_count == 2
        permission_repository.create_permissions.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_grant_admin_permission_to_the_role_created_by_a_concurrent_worker_when_it_has_none(
        self, use_case, user_repository, role_repository, permission_repository, command
    ):
        # Arrange
        concurrent_role = RoleFactory(id=5, name=BootstrapAdminUseCase.BOOTSTRAP_ADMIN_ROLE_NAME, permissions=[])
        user_repository.get_first_admin_user.return_value = UserNotFoundError()
        role_repository.get_role_with_permissions_and_limits_by_name.side_effect = [
            RoleNotFoundError(name=BootstrapAdminUseCase.BOOTSTRAP_ADMIN_ROLE_NAME),
            concurrent_role,
        ]
        role_repository.create_role.return_value = RoleAlreadyExistsError(name=BootstrapAdminUseCase.BOOTSTRAP_ADMIN_ROLE_NAME)
        user_repository.get_user_by_email.return_value = UserFactory(id=11, email=command.email, role_id=5)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert result == BootstrapAdminUseCaseSuccess(user_id=11, email=command.email, role_id=5)
        permission_repository.create_permissions.assert_awaited_once_with(role_id=5, permissions=[PermissionType.ADMIN])

    @pytest.mark.asyncio
    async def test_should_return_role_not_found_error_when_the_concurrently_created_role_cannot_be_read_back(
        self, use_case, user_repository, role_repository, permission_repository, command
    ):
        # Arrange
        user_repository.get_first_admin_user.return_value = UserNotFoundError()
        role_repository.get_role_with_permissions_and_limits_by_name.return_value = RoleNotFoundError(
            name=BootstrapAdminUseCase.BOOTSTRAP_ADMIN_ROLE_NAME
        )
        role_repository.create_role.return_value = RoleAlreadyExistsError(name=BootstrapAdminUseCase.BOOTSTRAP_ADMIN_ROLE_NAME)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert result == RoleNotFoundError(name=BootstrapAdminUseCase.BOOTSTRAP_ADMIN_ROLE_NAME)
        permission_repository.create_permissions.assert_not_awaited()
        user_repository.create_user.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_reuse_the_user_created_by_a_concurrent_worker_when_create_user_conflicts(
        self, use_case, user_repository, role_repository, command
    ):
        # Arrange: another worker inserted the user between our read and our insert
        role = RoleFactory(id=5, name=BootstrapAdminUseCase.BOOTSTRAP_ADMIN_ROLE_NAME, permissions=[PermissionType.ADMIN])
        concurrent_user = UserFactory(id=11, email=command.email, role_id=5)
        user_repository.get_first_admin_user.return_value = UserNotFoundError()
        role_repository.get_role_with_permissions_and_limits_by_name.return_value = role
        user_repository.get_user_by_email.side_effect = [UserNotFoundError(email=command.email), concurrent_user]
        user_repository.create_user.return_value = UserAlreadyExistsError(email=command.email)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert result == BootstrapAdminUseCaseSuccess(user_id=11, email=command.email, role_id=5)
        assert user_repository.get_user_by_email.await_count == 2
        user_repository.update_user.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_user_not_found_error_when_the_concurrently_created_user_cannot_be_read_back(
        self, use_case, user_repository, role_repository, command
    ):
        # Arrange
        role = RoleFactory(id=5, name=BootstrapAdminUseCase.BOOTSTRAP_ADMIN_ROLE_NAME, permissions=[PermissionType.ADMIN])
        user_repository.get_first_admin_user.return_value = UserNotFoundError()
        role_repository.get_role_with_permissions_and_limits_by_name.return_value = role
        user_repository.get_user_by_email.return_value = UserNotFoundError(email=command.email)
        user_repository.create_user.return_value = UserAlreadyExistsError(email=command.email)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert result == UserNotFoundError(email=command.email)
        user_repository.update_user.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_role_not_found_error_when_the_role_disappeared_before_the_user_is_created(
        self, use_case, user_repository, role_repository, command
    ):
        # Arrange
        role = RoleFactory(id=5, name=BootstrapAdminUseCase.BOOTSTRAP_ADMIN_ROLE_NAME, permissions=[PermissionType.ADMIN])
        user_repository.get_first_admin_user.return_value = UserNotFoundError()
        role_repository.get_role_with_permissions_and_limits_by_name.return_value = role
        user_repository.get_user_by_email.return_value = UserNotFoundError(email=command.email)
        user_repository.create_user.return_value = RoleNotFoundError(id=5)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert result == RoleNotFoundError(id=5)
        user_repository.update_user.assert_not_awaited()
