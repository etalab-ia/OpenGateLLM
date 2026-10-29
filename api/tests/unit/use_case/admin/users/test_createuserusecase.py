from unittest.mock import create_autospec

import pytest

from api.domain.organization.errors import OrganizationNotFoundError
from api.domain.role import RoleRepository
from api.domain.role.entities import PermissionType
from api.domain.role.errors import RoleNotFoundError
from api.domain.user import UserAuthorization, UserPasswordEncoder, UserRepository
from api.domain.user.errors import UserAlreadyExistsError
from api.tests.unit.use_case.factories import RoleFactory, UserFactory
from api.use_cases.admin.users import CreateUserCommand, CreateUserUseCase, CreateUserUseCaseSuccess


@pytest.fixture
def mock_user_repository():
    return create_autospec(UserRepository, instance=True, spec_set=True)


@pytest.fixture
def mock_role_repository():
    repository = create_autospec(RoleRepository, instance=True, spec_set=True)
    repository.get_role_with_permissions_and_limits_by_id.return_value = RoleFactory(id=10, permissions=[])
    return repository


@pytest.fixture
def mock_user_password_encoder():
    encoder = create_autospec(UserPasswordEncoder, instance=True, spec_set=True)
    encoder.encode_password.return_value = "encoded:s3cr3t"
    return encoder


@pytest.fixture
def mock_user_authorization():
    return create_autospec(UserAuthorization, instance=True, spec_set=True)


@pytest.fixture
def use_case(mock_user_repository, mock_role_repository, mock_user_password_encoder, mock_user_authorization):
    return CreateUserUseCase(
        user_repository=mock_user_repository,
        role_repository=mock_role_repository,
        user_password_encoder=mock_user_password_encoder,
        user_authorization=mock_user_authorization,
    )


@pytest.fixture
def default_command():
    return CreateUserCommand(
        email="newuser@test.com",
        password="s3cr3t",
        role_id=10,
        organization_id=5,
    )


class TestCreateUserUseCase:
    @pytest.mark.asyncio
    async def test_should_create_user_with_default_values(
        self, use_case, mock_user_repository, mock_role_repository, mock_user_password_encoder, mock_user_authorization
    ):
        # Arrange
        command = CreateUserCommand(
            email="newuser@test.com",
            password="s3cr3t",
            role_id=10,
            name="New User",
            organization_id=5,
            priority=2,
        )
        user = UserFactory(
            id=42,
            email="newuser@test.com",
            name="New User",
            role_id=10,
            organization_id=5,
            priority=2,
        )
        mock_user_repository.create_user.return_value = user

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, CreateUserUseCaseSuccess)
        assert result.user.id == 42
        assert result.user.email == "newuser@test.com"

        mock_role_repository.get_role_with_permissions_and_limits_by_id.assert_awaited_once_with(role_id=10)
        mock_user_password_encoder.encode_password.assert_called_once_with(password="s3cr3t")
        mock_user_repository.create_user.assert_awaited_once_with(
            email="newuser@test.com",
            role_id=10,
            name="New User",
            expires=None,
            organization_id=5,
            password="encoded:s3cr3t",
            priority=2,
        )
        mock_user_authorization.attach_admin_to_platform.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_attach_the_user_to_the_platform_as_admin_when_the_role_is_admin(
        self, use_case, mock_user_repository, mock_role_repository, mock_user_authorization, default_command
    ):
        # Arrange
        mock_role_repository.get_role_with_permissions_and_limits_by_id.return_value = RoleFactory(id=10, permissions=[PermissionType.ADMIN])
        mock_user_repository.create_user.return_value = UserFactory(id=42, role_id=10, organization_id=5)

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, CreateUserUseCaseSuccess)
        mock_user_authorization.attach_admin_to_platform.assert_awaited_once_with(user_id=42)

    @pytest.mark.asyncio
    async def test_should_return_role_not_found_error_without_creating_the_user_when_the_role_id_does_not_exist(
        self, use_case, mock_user_repository, mock_role_repository, mock_user_authorization, default_command
    ):
        # Arrange
        mock_role_repository.get_role_with_permissions_and_limits_by_id.return_value = RoleNotFoundError(id=10)

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, RoleNotFoundError)
        assert result.id == 10
        mock_user_repository.create_user.assert_not_awaited()
        mock_user_authorization.attach_admin_to_platform.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_user_already_exists_error_without_attaching_an_admin_when_a_user_has_the_same_email(
        self, use_case, mock_user_repository, mock_role_repository, mock_user_authorization, default_command
    ):
        # Arrange
        mock_role_repository.get_role_with_permissions_and_limits_by_id.return_value = RoleFactory(id=10, permissions=[PermissionType.ADMIN])
        mock_user_repository.create_user.return_value = UserAlreadyExistsError(email="newuser@test.com")

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, UserAlreadyExistsError)
        assert result.email == "newuser@test.com"
        mock_user_authorization.attach_admin_to_platform.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_organization_not_found_error_when_the_organisation_does_not_exist(
        self, use_case, mock_user_repository, default_command
    ):
        # Arrange
        mock_user_repository.create_user.return_value = OrganizationNotFoundError(id=5)

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, OrganizationNotFoundError)
        assert result.id == 5
