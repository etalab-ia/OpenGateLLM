from unittest.mock import AsyncMock, Mock

from pydantic import SecretStr
import pytest

from api.domain.organization.errors import OrganizationNotFoundError
from api.domain.role.errors import RoleNotFoundError
from api.domain.user.errors import IncorrectCurrentPasswordError, UserAlreadyExistsError, UserNotFoundError
from api.tests.unit.use_case.factories import UserFactory
from api.use_cases.admin.users import UpdateUserCommand, UpdateUserUseCase, UpdateUserUseCaseSuccess


@pytest.fixture
def user_repository():
    return AsyncMock()


@pytest.fixture
def user_password_encoder():
    encoder = Mock()
    encoder.encode_password.side_effect = lambda password: f"encoded-{password}"
    encoder.validate_password.return_value = True
    return encoder


@pytest.fixture
def use_case(user_repository, user_password_encoder):
    return UpdateUserUseCase(user_repository=user_repository, user_password_encoder=user_password_encoder)


@pytest.fixture
def sample_user():
    return UserFactory(id=42, organization_id=7, budget=100.0, expires=None, priority=1)


class TestUpdateUserUseCase:
    @pytest.mark.asyncio
    async def test_should_return_updated_user_when_user_exists(self, use_case, user_repository, sample_user):
        # Arrange
        user_repository.get_user_by_id.return_value = sample_user
        user_repository.update_user.side_effect = lambda user: user

        # Act
        result = await use_case.execute(UpdateUserCommand(user_id=sample_user.id, email="new@example.com", role_id=3))

        # Assert
        assert isinstance(result, UpdateUserUseCaseSuccess)
        assert result.user.email == "new@example.com"
        assert result.user.role_id == 3
        user_repository.get_user_by_id.assert_called_once_with(user_id=sample_user.id)
        user_repository.update_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_keep_non_nullable_fields_and_clear_nullable_fields_when_fields_are_none(self, use_case, user_repository, sample_user):
        # Arrange
        user_repository.get_user_by_id.return_value = sample_user
        user_repository.update_user.side_effect = lambda user: user

        # Act
        result = await use_case.execute(UpdateUserCommand(user_id=sample_user.id))

        # Assert
        assert isinstance(result, UpdateUserUseCaseSuccess)
        # Non-nullable columns keep their current value.
        assert result.user.email == sample_user.email
        assert result.user.role_id == sample_user.role_id
        assert result.user.priority == sample_user.priority
        assert result.user.password == sample_user.password
        # Nullable columns are cleared.
        assert result.user.name is None
        assert result.user.organization_id is None
        assert result.user.budget is None
        assert result.user.expires is None

    @pytest.mark.asyncio
    async def test_should_keep_current_password_when_no_new_password(self, use_case, user_repository, user_password_encoder, sample_user):
        # Arrange
        user_repository.get_user_by_id.return_value = sample_user.model_copy(update={"password": SecretStr("encoded-old")})
        user_repository.update_user.side_effect = lambda user: user

        # Act
        result = await use_case.execute(UpdateUserCommand(user_id=sample_user.id, current_password="old"))

        # Assert
        assert isinstance(result, UpdateUserUseCaseSuccess)
        assert result.user.password == SecretStr("encoded-old")
        user_password_encoder.encode_password.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_encode_new_password_without_verification_when_no_current_password(
        self, use_case, user_repository, user_password_encoder, sample_user
    ):
        # Arrange
        user_repository.get_user_by_id.return_value = sample_user
        user_repository.update_user.side_effect = lambda user: user

        # Act
        result = await use_case.execute(UpdateUserCommand(user_id=sample_user.id, new_password="secret"))

        # Assert
        assert isinstance(result, UpdateUserUseCaseSuccess)
        assert result.user.password == SecretStr("encoded-secret")
        user_password_encoder.encode_password.assert_called_once_with(password="secret")
        user_password_encoder.validate_password.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_encode_new_password_when_current_password_is_correct(self, use_case, user_repository, user_password_encoder, sample_user):
        # Arrange
        user_repository.get_user_by_id.return_value = sample_user.model_copy(update={"password": SecretStr("encoded-old")})
        user_repository.update_user.side_effect = lambda user: user
        user_password_encoder.validate_password.return_value = True

        # Act
        result = await use_case.execute(UpdateUserCommand(user_id=sample_user.id, current_password="old", new_password="secret"))

        # Assert
        assert isinstance(result, UpdateUserUseCaseSuccess)
        assert result.user.password == SecretStr("encoded-secret")
        user_password_encoder.validate_password.assert_called_once_with(password="old", encoded_password="encoded-old")

    @pytest.mark.asyncio
    async def test_should_return_user_not_found_error_when_user_does_not_exist(self, use_case, user_repository):
        # Arrange
        user_repository.get_user_by_id.return_value = UserNotFoundError(id=99)

        # Act
        result = await use_case.execute(UpdateUserCommand(user_id=99, email="new@example.com"))

        # Assert
        assert isinstance(result, UserNotFoundError)
        assert result.id == 99
        user_repository.update_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_incorrect_current_password_error_when_current_password_is_wrong(
        self, use_case, user_repository, user_password_encoder, sample_user
    ):
        # Arrange
        user_repository.get_user_by_id.return_value = sample_user.model_copy(update={"password": SecretStr("encoded-old")})
        user_password_encoder.validate_password.return_value = False

        # Act
        result = await use_case.execute(UpdateUserCommand(user_id=sample_user.id, current_password="wrong", new_password="secret"))

        # Assert
        assert isinstance(result, IncorrectCurrentPasswordError)
        assert result.user_id == sample_user.id
        user_repository.update_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_incorrect_current_password_error_when_user_has_no_password(
        self, use_case, user_repository, user_password_encoder, sample_user
    ):
        # Arrange
        user_repository.get_user_by_id.return_value = sample_user.model_copy(update={"password": None})

        # Act
        result = await use_case.execute(UpdateUserCommand(user_id=sample_user.id, current_password="old", new_password="secret"))

        # Assert
        assert isinstance(result, IncorrectCurrentPasswordError)
        user_password_encoder.validate_password.assert_not_called()
        user_repository.update_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_role_not_found_error_when_repository_reports_unknown_role(self, use_case, user_repository, sample_user):
        # Arrange
        user_repository.get_user_by_id.return_value = sample_user
        user_repository.update_user.return_value = RoleNotFoundError(id=3)

        # Act
        result = await use_case.execute(UpdateUserCommand(user_id=sample_user.id, role_id=3))

        # Assert
        assert isinstance(result, RoleNotFoundError)
        assert result.id == 3

    @pytest.mark.asyncio
    async def test_should_return_organization_not_found_error_when_repository_reports_unknown_organization(
        self, use_case, user_repository, sample_user
    ):
        # Arrange
        user_repository.get_user_by_id.return_value = sample_user
        user_repository.update_user.return_value = OrganizationNotFoundError(id=8)

        # Act
        result = await use_case.execute(UpdateUserCommand(user_id=sample_user.id, organization_id=8))

        # Assert
        assert isinstance(result, OrganizationNotFoundError)
        assert result.id == 8

    @pytest.mark.asyncio
    async def test_should_return_user_already_exists_error_when_email_is_taken(self, use_case, user_repository, sample_user):
        # Arrange
        user_repository.get_user_by_id.return_value = sample_user
        user_repository.update_user.return_value = UserAlreadyExistsError(email="taken@example.com")

        # Act
        result = await use_case.execute(UpdateUserCommand(user_id=sample_user.id, email="taken@example.com"))

        # Assert
        assert isinstance(result, UserAlreadyExistsError)
        assert result.email == "taken@example.com"
