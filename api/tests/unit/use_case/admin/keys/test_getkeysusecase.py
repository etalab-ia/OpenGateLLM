from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from api.domain import EntitiesPage, SortField, SortOrder
from api.domain.key.entities import Key
from api.use_cases.admin.keys import GetKeysCommand, GetKeysUseCase, GetKeysUseCaseSuccess


@pytest.fixture
def key_repository():
    return AsyncMock()


@pytest.fixture
def use_case(key_repository):
    return GetKeysUseCase(key_repository=key_repository)


class TestGetKeysUseCase:
    @pytest.mark.asyncio
    async def test_should_return_keys_page(self, use_case, key_repository):
        # Arrange
        key = Key(
            id=1,
            name="my-key",
            user_id=42,
            value="sk-masked...value",
            expires=None,
            created=datetime(2030, 1, 1, tzinfo=UTC),
        )
        key_repository.get_keys_page.return_value = EntitiesPage(total=1, data=[key])
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
        key_repository.get_keys_page.assert_awaited_once_with(
            user_id=42,
            limit=10,
            offset=0,
            sort_by=SortField.ID,
            sort_order=SortOrder.ASC,
            exclude_expired=True,
        )

    @pytest.mark.asyncio
    async def test_should_exclude_expired_keys_by_default(self, use_case, key_repository):
        # Arrange
        key_repository.get_keys_page.return_value = EntitiesPage(total=0, data=[])
        command = GetKeysCommand(
            user_id=42,
            offset=0,
            limit=10,
            sort_by=SortField.ID,
            sort_order=SortOrder.ASC,
        )

        # Act
        await use_case.execute(command)

        # Assert
        assert key_repository.get_keys_page.await_args.kwargs["exclude_expired"] is True

    @pytest.mark.asyncio
    async def test_should_forward_exclude_expired_to_the_repository(self, use_case, key_repository):
        # Arrange
        key_repository.get_keys_page.return_value = EntitiesPage(total=0, data=[])
        command = GetKeysCommand(
            user_id=42,
            offset=0,
            limit=10,
            sort_by=SortField.ID,
            sort_order=SortOrder.ASC,
            exclude_expired=False,
        )

        # Act
        await use_case.execute(command)

        # Assert
        assert key_repository.get_keys_page.await_args.kwargs["exclude_expired"] is False
