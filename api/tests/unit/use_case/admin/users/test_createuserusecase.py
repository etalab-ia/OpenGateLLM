from unittest.mock import AsyncMock, MagicMock

import pytest

from api.domain.organization.errors import OrganizationNotFoundError
from api.domain.role.errors import RoleNotFoundError
from api.domain.user.errors import UserAlreadyExistsError
from api.tests.unit.use_case.factories import UserFactory
from api.use_cases.admin.users import CreateUserCommand, CreateUserUseCase, CreateUserUseCaseSuccess


@pytest.fixture
def user_repository():
    return AsyncMock()


@pytest.fixture
def user_password_encoder():
    encoder = MagicMock()
    encoder.encode_password.return_value = "encoded:s3cr3t"
    return encoder


@pytest.fixture
def use_case(user_repository, user_password_encoder):
    return CreateUserUseCase(user_repository=user_repository, user_password_encoder=user_password_encoder)


@pytest.fixture
def default_command():
    return CreateUserCommand(
        email="newuser@test.com",
        password="s3cr3t",
        role_id=10,
    )


class TestCreateUserUseCase:
    @pytest.mark.asyncio
    async def test_should_create_user_with_default_values(self, use_case, user_repository, user_password_encoder):
        # Arrange
        command = CreateUserCommand(
            email="newuser@test.com",
            password="s3cr3t",
            role_id=10,
            name="New User",
            organization_id=5,
            budget=100.0,
            priority=2,
        )
        user = UserFactory(
            id=42,
            email="newuser@test.com",
            name="New User",
            role=10,
            organization_id=5,
            budget=100.0,
            priority=2,
        )
        user_repository.create_user.return_value = user

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, CreateUserUseCaseSuccess)
        assert result.user.id == 42
        assert result.user.email == "newuser@test.com"

        user_password_encoder.encode_password.assert_called_once_with(password="s3cr3t")
        user_repository.create_user.assert_awaited_once()
        assert user_repository.create_user.call_args.kwargs == {
            "email": "newuser@test.com",
            "role_id": 10,
            "name": "New User",
            "expires": None,
            "organization_id": 5,
            "password": "encoded:s3cr3t",
            "budget": 100.0,
            "priority": 2,
        }

    @pytest.mark.asyncio
    async def test_should_return_user_already_exists_error_when_a_user_has_the_same_email(self, use_case, user_repository, default_command):
        # Arrange

        user_repository.create_user.return_value = UserAlreadyExistsError(email="newuser@test.com")

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, UserAlreadyExistsError)
        assert result.email == "newuser@test.com"

    @pytest.mark.asyncio
    async def test_should_return_role_not_found_error_when_the_role_id_does_not_exist(self, use_case, user_repository, default_command):
        # Arrange

        user_repository.create_user.return_value = RoleNotFoundError(id=10)

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, RoleNotFoundError)
        assert result.id == 10

    @pytest.mark.asyncio
    async def test_should_return_organization_not_found_error_when_the_organisation_does_not_exist(self, use_case, user_repository, default_command):
        # Arrange

        user_repository.create_user.return_value = OrganizationNotFoundError(id=5)

        # Act
        result = await use_case.execute(default_command)

        # Assert
        assert isinstance(result, OrganizationNotFoundError)
        assert result.id == 5
