from datetime import UTC, datetime
from unittest.mock import create_autospec

from pydantic import SecretStr
import pytest

from api.domain.organization.errors import OrganizationNotFoundError
from api.domain.role.errors import RoleNotFoundError
from api.domain.user import UserAuthorization, UserPasswordEncoder, UserRepository
from api.domain.user.errors import IncorrectCurrentPasswordError, UserAlreadyExistsError, UserCannotUpdateUserError, UserNotFoundError
from api.tests.unit.use_case.factories import UserFactory
from api.use_cases.admin.users import UpdateUserCommand, UpdateUserUseCase, UpdateUserUseCaseSuccess


@pytest.fixture
def mock_user_repository():
    return create_autospec(UserRepository, instance=True, spec_set=True)


@pytest.fixture
def mock_user_password_encoder():
    encoder = create_autospec(UserPasswordEncoder, instance=True, spec_set=True)
    encoder.encode_password.side_effect = lambda password: f"encoded-{password}"
    encoder.validate_password.return_value = True
    return encoder


@pytest.fixture
def mock_user_authorization():
    authorization = create_autospec(UserAuthorization, instance=True, spec_set=True)
    authorization.can_update_user.return_value = True
    return authorization


@pytest.fixture
def use_case(mock_user_repository, mock_user_password_encoder, mock_user_authorization):
    return UpdateUserUseCase(
        user_repository=mock_user_repository,
        user_password_encoder=mock_user_password_encoder,
        user_authorization=mock_user_authorization,
    )


@pytest.fixture
def sample_user():
    return UserFactory(id=42, organization_id=7, expires=None, priority=1)


def full_command(user, **overrides) -> UpdateUserCommand:
    """Command replacing every persisted field with the current user values, unless overridden."""
    command = UpdateUserCommand(
        authenticated_user_id=1,
        user_id=user.id,
        email=user.email,
        name=user.name,
        role_id=user.role_id,
        organization_id=user.organization_id,
        expires=user.expires,
        priority=user.priority,
    )
    for field, value in overrides.items():
        setattr(command, field, value)
    return command


class TestUpdateUserUseCase:
    @pytest.mark.asyncio
    async def test_should_return_updated_user_when_user_exists(self, use_case, mock_user_repository, sample_user):
        # Arrange
        mock_user_repository.get_user_by_id.return_value = sample_user
        mock_user_repository.update_user.side_effect = lambda user: user

        # Act
        result = await use_case.execute(full_command(sample_user, email="new@example.com", role_id=3))

        # Assert
        assert isinstance(result, UpdateUserUseCaseSuccess)
        assert result.user.email == "new@example.com"
        assert result.user.role_id == 3
        mock_user_repository.get_user_by_id.assert_called_once_with(user_id=sample_user.id)
        mock_user_repository.update_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_clear_nullable_fields_when_command_fields_are_none(self, use_case, mock_user_repository, sample_user):
        # Arrange
        mock_user_repository.get_user_by_id.return_value = sample_user
        mock_user_repository.update_user.side_effect = lambda user: user

        # Act
        result = await use_case.execute(full_command(sample_user, name=None, expires=None))

        # Assert
        assert isinstance(result, UpdateUserUseCaseSuccess)
        assert result.user.name is None
        assert result.user.expires is None
        # The other persisted fields keep the values sent by the command.
        assert result.user.email == sample_user.email
        assert result.user.role_id == sample_user.role_id
        assert result.user.organization_id == sample_user.organization_id
        assert result.user.priority == sample_user.priority
        assert result.user.password == sample_user.password

    @pytest.mark.asyncio
    async def test_should_replace_every_persisted_field_with_the_command_values(self, use_case, mock_user_repository, sample_user):
        # Arrange
        mock_user_repository.get_user_by_id.return_value = sample_user
        mock_user_repository.update_user.side_effect = lambda user: user

        # Act
        result = await use_case.execute(
            full_command(
                sample_user,
                email="new@example.com",
                name="New Name",
                role_id=3,
                organization_id=8,
                expires=datetime(2030, 1, 1, tzinfo=UTC),
                priority=5,
            )
        )

        # Assert
        assert isinstance(result, UpdateUserUseCaseSuccess)
        assert result.user.email == "new@example.com"
        assert result.user.name == "New Name"
        assert result.user.role_id == 3
        assert result.user.organization_id == 8
        assert result.user.expires == datetime(2030, 1, 1, tzinfo=UTC)
        assert result.user.priority == 5

    @pytest.mark.asyncio
    async def test_should_keep_current_password_when_no_new_password(self, use_case, mock_user_repository, mock_user_password_encoder, sample_user):
        # Arrange
        mock_user_repository.get_user_by_id.return_value = sample_user.model_copy(update={"password": SecretStr("encoded-old")})
        mock_user_repository.update_user.side_effect = lambda user: user

        # Act
        result = await use_case.execute(full_command(sample_user, current_password="old"))

        # Assert
        assert isinstance(result, UpdateUserUseCaseSuccess)
        assert result.user.password == SecretStr("encoded-old")
        mock_user_password_encoder.encode_password.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_encode_new_password_without_verification_when_no_current_password(
        self, use_case, mock_user_repository, mock_user_password_encoder, sample_user
    ):
        # Arrange
        mock_user_repository.get_user_by_id.return_value = sample_user
        mock_user_repository.update_user.side_effect = lambda user: user

        # Act
        result = await use_case.execute(full_command(sample_user, new_password="secret"))

        # Assert
        assert isinstance(result, UpdateUserUseCaseSuccess)
        assert result.user.password == SecretStr("encoded-secret")
        mock_user_password_encoder.encode_password.assert_called_once_with(password="secret")
        mock_user_password_encoder.validate_password.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_encode_new_password_when_current_password_is_correct(
        self, use_case, mock_user_repository, mock_user_password_encoder, sample_user
    ):
        # Arrange
        mock_user_repository.get_user_by_id.return_value = sample_user.model_copy(update={"password": SecretStr("encoded-old")})
        mock_user_repository.update_user.side_effect = lambda user: user
        mock_user_password_encoder.validate_password.return_value = True

        # Act
        result = await use_case.execute(full_command(sample_user, current_password="old", new_password="secret"))

        # Assert
        assert isinstance(result, UpdateUserUseCaseSuccess)
        assert result.user.password == SecretStr("encoded-secret")
        mock_user_password_encoder.validate_password.assert_called_once_with(password="old", encoded_password="encoded-old")

    @pytest.mark.asyncio
    async def test_should_return_user_cannot_update_user_error_without_reading_when_the_user_is_not_allowed(
        self, use_case, mock_user_repository, mock_user_authorization, sample_user
    ):
        # Arrange
        mock_user_authorization.can_update_user.return_value = False

        # Act
        result = await use_case.execute(full_command(sample_user))

        # Assert
        assert isinstance(result, UserCannotUpdateUserError)
        assert result.user_id == 1
        mock_user_authorization.can_update_user.assert_awaited_once_with(user_id=1, target_user_id=sample_user.id)
        mock_user_repository.get_user_by_id.assert_not_awaited()
        mock_user_repository.update_user.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_user_not_found_error_when_user_does_not_exist(self, use_case, mock_user_repository):
        # Arrange
        mock_user_repository.get_user_by_id.return_value = UserNotFoundError(id=99)

        # Act
        result = await use_case.execute(full_command(UserFactory(id=99), email="new@example.com"))

        # Assert
        assert isinstance(result, UserNotFoundError)
        assert result.id == 99
        mock_user_repository.update_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_incorrect_current_password_error_when_current_password_is_wrong(
        self, use_case, mock_user_repository, mock_user_password_encoder, sample_user
    ):
        # Arrange
        mock_user_repository.get_user_by_id.return_value = sample_user.model_copy(update={"password": SecretStr("encoded-old")})
        mock_user_password_encoder.validate_password.return_value = False

        # Act
        result = await use_case.execute(full_command(sample_user, current_password="wrong", new_password="secret"))

        # Assert
        assert isinstance(result, IncorrectCurrentPasswordError)
        assert result.user_id == sample_user.id
        mock_user_repository.update_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_incorrect_current_password_error_when_user_has_no_password(
        self, use_case, mock_user_repository, mock_user_password_encoder, sample_user
    ):
        # Arrange
        mock_user_repository.get_user_by_id.return_value = sample_user.model_copy(update={"password": None})

        # Act
        result = await use_case.execute(full_command(sample_user, current_password="old", new_password="secret"))

        # Assert
        assert isinstance(result, IncorrectCurrentPasswordError)
        mock_user_password_encoder.validate_password.assert_not_called()
        mock_user_repository.update_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_role_not_found_error_when_repository_reports_unknown_role(self, use_case, mock_user_repository, sample_user):
        # Arrange
        mock_user_repository.get_user_by_id.return_value = sample_user
        mock_user_repository.update_user.return_value = RoleNotFoundError(id=3)

        # Act
        result = await use_case.execute(full_command(sample_user, role_id=3))

        # Assert
        assert isinstance(result, RoleNotFoundError)
        assert result.id == 3

    @pytest.mark.asyncio
    async def test_should_return_organization_not_found_error_when_repository_reports_unknown_organization(
        self, use_case, mock_user_repository, sample_user
    ):
        # Arrange
        mock_user_repository.get_user_by_id.return_value = sample_user
        mock_user_repository.update_user.return_value = OrganizationNotFoundError(id=8)

        # Act
        result = await use_case.execute(full_command(sample_user, organization_id=8))

        # Assert
        assert isinstance(result, OrganizationNotFoundError)
        assert result.id == 8

    @pytest.mark.asyncio
    async def test_should_return_user_already_exists_error_when_email_is_taken(self, use_case, mock_user_repository, sample_user):
        # Arrange
        mock_user_repository.get_user_by_id.return_value = sample_user
        mock_user_repository.update_user.return_value = UserAlreadyExistsError(email="taken@example.com")

        # Act
        result = await use_case.execute(full_command(sample_user, email="taken@example.com"))

        # Assert
        assert isinstance(result, UserAlreadyExistsError)
        assert result.email == "taken@example.com"
