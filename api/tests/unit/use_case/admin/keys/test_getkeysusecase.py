from unittest.mock import create_autospec

import pytest

from api.domain import EntitiesPage, SortField, SortOrder
from api.domain.key import KeyRepository
from api.domain.key.entities import KeyStatus
from api.tests.unit.use_case.factories import KeyFactory
from api.use_cases.admin.keys import GetKeysCommand, GetKeysUseCase, GetKeysUseCaseSuccess


@pytest.fixture
def mock_key_repository():
    return create_autospec(KeyRepository, instance=True, spec_set=True)


@pytest.fixture
def use_case(mock_key_repository):
    return GetKeysUseCase(key_repository=mock_key_repository)


class TestGetKeysUseCase:
    @pytest.mark.asyncio
    async def test_should_return_keys_page(self, use_case, mock_key_repository):
        # Arrange
        key = KeyFactory(id=1, name="my-key", user_id=42)
        mock_key_repository.get_keys_page.return_value = EntitiesPage(total=1, data=[key])
        command = GetKeysCommand(
            user_id=42,
            offset=0,
            limit=10,
            sort_by=SortField.ID,
            sort_order=SortOrder.ASC,
        )

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, GetKeysUseCaseSuccess)
        assert result.key_page.total == 1
        assert result.key_page.data == [key]
        mock_key_repository.get_keys_page.assert_awaited_once_with(
            user_id=42,
            limit=10,
            offset=0,
            sort_by=SortField.ID,
            sort_order=SortOrder.ASC,
            status=None,
        )

    @pytest.mark.asyncio
    async def test_should_forward_status_to_the_repository(self, use_case, mock_key_repository):
        # Arrange
        mock_key_repository.get_keys_page.return_value = EntitiesPage(total=0, data=[])
        command = GetKeysCommand(
            user_id=42,
            offset=0,
            limit=10,
            sort_by=SortField.ID,
            sort_order=SortOrder.ASC,
            status=KeyStatus.ACTIVE,
        )

        # Act
        await use_case.execute(command)

        # Assert
        assert mock_key_repository.get_keys_page.await_args.kwargs["status"] is KeyStatus.ACTIVE
