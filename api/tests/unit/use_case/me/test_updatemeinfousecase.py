from unittest.mock import AsyncMock, Mock

from pydantic import SecretStr
import pytest

from api.domain.user.errors import IncorrectCurrentPasswordError, UserAlreadyExistsError, UserNotFoundError
from api.tests.unit.use_case.factories import UserFactory
from api.use_cases.me import UpdateMeCommand, UpdateMeUseCase, UpdateMeUseCaseSuccess


def _command(user, **overrides) -> UpdateMeCommand:
    return UpdateMeCommand(
        user_id=overrides.pop("user_id", user.id),
        email=overrides.pop("email", user.email),
        name=overrides.pop("name", user.name),
        **overrides,
    )


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
    return UpdateMeUseCase(user_repository=user_repository, user_password_encoder=user_password_encoder)


@pytest.fixture
def sample_user():
    return UserFactory(id=42, organization_id=7, budget=100.0, expires=None, priority=1)


class TestUpdateMeInfoUseCase:
    @pytest.mark.asyncio
    async def test_should_return_updated_user_when_user_exists(self, use_case, user_repository, sample_user):
        # Arrange
        user_repository.get_user_by_id.return_value = sample_user
        user_repository.update_user.side_effect = lambda user: user

        # Act
        result = await use_case.execute(_command(sample_user, email="new@example.com", name="New Name"))

        # Assert
        assert isinstance(result, UpdateMeUseCaseSuccess)
        assert result.user.email == "new@example.com"
        assert result.user.name == "New Name"
        user_repository.get_user_by_id.assert_called_once_with(user_id=sample_user.id)
        user_repository.update_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_keep_other_fields_when_updating_name_and_email(self, use_case, user_repository, sample_user):
        # Arrange
        user_repository.get_user_by_id.return_value = sample_user
        user_repository.update_user.side_effect = lambda user: user

        # Act
        result = await use_case.execute(_command(sample_user))

        # Assert
        assert isinstance(result, UpdateMeUseCaseSuccess)
        assert result.user.email == sample_user.email
        assert result.user.name == sample_user.name
        assert result.user.role_id == sample_user.role_id
        assert result.user.priority == sample_user.priority
        assert result.user.password == sample_user.password
        assert result.user.organization_id == sample_user.organization_id
        assert result.user.budget == sample_user.budget
        assert result.user.expires == sample_user.expires

    @pytest.mark.asyncio
    async def test_should_keep_current_password_when_no_new_password(self, use_case, user_repository, user_password_encoder, sample_user):
        # Arrange
        user_repository.get_user_by_id.return_value = sample_user.model_copy(update={"password": SecretStr("encoded-old")})
        user_repository.update_user.side_effect = lambda user: user

        # Act
        result = await use_case.execute(_command(sample_user, current_password="old"))

        # Assert
        assert isinstance(result, UpdateMeUseCaseSuccess)
        assert result.user.password == SecretStr("encoded-old")
        user_password_encoder.encode_password.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_ignore_new_password_when_current_password_is_none(self, use_case, user_repository, user_password_encoder, sample_user):
        # Arrange
        user_repository.get_user_by_id.return_value = sample_user.model_copy(update={"password": SecretStr("encoded-old")})
        user_repository.update_user.side_effect = lambda user: user

        # Act
        result = await use_case.execute(_command(sample_user, new_password="secret"))

        # Assert
        assert isinstance(result, UpdateMeUseCaseSuccess)
        assert result.user.password == SecretStr("encoded-old")
        user_password_encoder.encode_password.assert_not_called()
        user_password_encoder.validate_password.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_encode_new_password_when_current_password_is_correct(self, use_case, user_repository, user_password_encoder, sample_user):
        # Arrange
        user_repository.get_user_by_id.return_value = sample_user.model_copy(update={"password": SecretStr("encoded-old")})
        user_repository.update_user.side_effect = lambda user: user
        user_password_encoder.validate_password.return_value = True

        # Act
        result = await use_case.execute(_command(sample_user, current_password="old", new_password="secret"))

        # Assert
        assert isinstance(result, UpdateMeUseCaseSuccess)
        assert result.user.password == SecretStr("encoded-secret")
        user_password_encoder.validate_password.assert_called_once_with(password="old", encoded_password="encoded-old")

    @pytest.mark.asyncio
    async def test_should_return_user_not_found_error_when_user_does_not_exist(self, use_case, user_repository):
        # Arrange
        user_repository.get_user_by_id.return_value = UserNotFoundError(id=99)

        # Act
        result = await use_case.execute(UpdateMeCommand(user_id=99, email="new@example.com", name="New Name"))

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
        result = await use_case.execute(_command(sample_user, current_password="wrong", new_password="secret"))

        # Assert
        assert isinstance(result, IncorrectCurrentPasswordError)
        assert result.user_id == sample_user.id
        user_repository.update_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_encode_new_password_without_verification_when_user_has_no_password(
        self, use_case, user_repository, user_password_encoder, sample_user
    ):
        # Arrange
        user_repository.get_user_by_id.return_value = sample_user.model_copy(update={"password": None})
        user_repository.update_user.side_effect = lambda user: user

        # Act
        result = await use_case.execute(_command(sample_user, current_password="old", new_password="secret"))

        # Assert
        assert isinstance(result, UpdateMeUseCaseSuccess)
        assert result.user.password == SecretStr("encoded-secret")
        user_password_encoder.encode_password.assert_called_once_with(password="secret")
        user_password_encoder.validate_password.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_user_already_exists_error_when_email_is_taken(self, use_case, user_repository, sample_user):
        # Arrange
        user_repository.get_user_by_id.return_value = sample_user
        user_repository.update_user.return_value = UserAlreadyExistsError(email="taken@example.com")

        # Act
        result = await use_case.execute(_command(sample_user, email="taken@example.com"))

        # Assert
        assert isinstance(result, UserAlreadyExistsError)
        assert result.email == "taken@example.com"
