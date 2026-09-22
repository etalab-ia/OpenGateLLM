from unittest.mock import create_autospec

import pytest

from api.domain.key import KeyRepository
from api.domain.key.errors import KeyNotFoundError
from api.tests.unit.use_case.factories import KeyFactory
from api.use_cases.admin.keys import UpdateKeyCommand, UpdateKeyUseCase, UpdateKeyUseCaseSuccess


@pytest.fixture
def mock_key_repository():
    return create_autospec(KeyRepository, instance=True, spec_set=True)


@pytest.fixture
def use_case(mock_key_repository):
    return UpdateKeyUseCase(key_repository=mock_key_repository)


class TestUpdateKeyUseCase:
    @pytest.mark.asyncio
    async def test_should_revoke_key_when_key_exists(self, use_case, mock_key_repository):
        # Arrange
        key = KeyFactory(id=42, user_id=1, revoked=False)
        revoked_key = key.with_revoked(True)
        mock_key_repository.get_key_by_id.return_value = key
        mock_key_repository.update_key.return_value = revoked_key
        command = UpdateKeyCommand(key_id=42, revoked=True)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, UpdateKeyUseCaseSuccess)
        assert result.key.revoked is True
        mock_key_repository.get_key_by_id.assert_awaited_once_with(42)
        mock_key_repository.update_key.assert_awaited_once_with(revoked_key)

    @pytest.mark.asyncio
    async def test_should_not_call_update_when_revoked_is_unchanged(self, use_case, mock_key_repository):
        # Arrange
        key = KeyFactory(id=42, user_id=1, revoked=True)
        mock_key_repository.get_key_by_id.return_value = key
        command = UpdateKeyCommand(key_id=42, revoked=True)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, UpdateKeyUseCaseSuccess)
        assert result.key == key
        mock_key_repository.update_key.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_key_not_found_error_when_key_does_not_exist(self, use_case, mock_key_repository):
        # Arrange
        mock_key_repository.get_key_by_id.return_value = KeyNotFoundError(id=99)
        command = UpdateKeyCommand(key_id=99, revoked=True)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, KeyNotFoundError)
        assert result.id == 99
        mock_key_repository.update_key.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_key_not_found_error_when_user_id_does_not_match_owner(self, use_case, mock_key_repository):
        # Arrange
        key = KeyFactory(id=42, user_id=1, revoked=False)
        mock_key_repository.get_key_by_id.return_value = key
        command = UpdateKeyCommand(key_id=42, user_id=99, revoked=True)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, KeyNotFoundError)
        assert result.id == 42
        mock_key_repository.update_key.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_revoke_key_when_user_id_matches_owner(self, use_case, mock_key_repository):
        # Arrange
        key = KeyFactory(id=42, user_id=1, revoked=False)
        revoked_key = key.with_revoked(True)
        mock_key_repository.get_key_by_id.return_value = key
        mock_key_repository.update_key.return_value = revoked_key
        command = UpdateKeyCommand(key_id=42, user_id=1, revoked=True)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, UpdateKeyUseCaseSuccess)
        assert result.key.revoked is True
        mock_key_repository.update_key.assert_awaited_once_with(revoked_key)

    @pytest.mark.asyncio
    async def test_should_propagate_key_not_found_error_from_update_key(self, use_case, mock_key_repository):
        # Arrange
        key = KeyFactory(id=42, user_id=1, revoked=False)
        mock_key_repository.get_key_by_id.return_value = key
        mock_key_repository.update_key.return_value = KeyNotFoundError(id=42)
        command = UpdateKeyCommand(key_id=42, revoked=True)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, KeyNotFoundError)
        assert result.id == 42
