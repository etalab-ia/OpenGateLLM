from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.domain import EntitiesPage, SortField, SortOrder
from api.domain.key.entities import Key
from api.infrastructure.fastapi.endpoints.admin.keys import get_keys
from api.infrastructure.fastapi.schemas.admin.keys import KeysResponse
from api.use_cases.admin.keys import GetKeysCommand, GetKeysUseCaseSuccess


@pytest.fixture
def mock_authenticated_user():
    return MagicMock(id=1)


class TestGetKeysEndpoint:
    @pytest.mark.asyncio
    async def test_should_map_key_page_to_keys_response(self, mock_authenticated_user):
        key = Key(
            id=1,
            name="my-key",
            user_id=42,
            value="sk-masked...value",
            expires=None,
            created=datetime(2030, 1, 1, tzinfo=UTC),
        )
        mock_use_case = MagicMock()
        mock_use_case.execute = AsyncMock(return_value=GetKeysUseCaseSuccess(key_page=EntitiesPage(total=1, data=[key])))

        result = await get_keys(
            user=None,
            offset=0,
            limit=10,
            sort_by=SortField.ID,
            sort_order=SortOrder.ASC,
            include_expired=False,
            get_keys_use_case=mock_use_case,
            authenticated_user=mock_authenticated_user,
        )

        assert isinstance(result, KeysResponse)
        assert result.total == 1
        assert result.offset == 0
        assert result.limit == 10
        assert len(result.data) == 1
        assert result.data[0].name == "my-key"
        assert result.data[0].user == 42
        mock_use_case.execute.assert_awaited_once_with(
            GetKeysCommand(user_id=None, offset=0, limit=10, sort_by=SortField.ID, sort_order=SortOrder.ASC, exclude_expired=True)
        )

    @pytest.mark.asyncio
    async def test_should_not_exclude_expired_keys_when_include_expired_is_set(self, mock_authenticated_user):
        mock_use_case = MagicMock()
        mock_use_case.execute = AsyncMock(return_value=GetKeysUseCaseSuccess(key_page=EntitiesPage(total=0, data=[])))

        await get_keys(
            user=None,
            offset=0,
            limit=10,
            sort_by=SortField.ID,
            sort_order=SortOrder.ASC,
            include_expired=True,
            get_keys_use_case=mock_use_case,
            authenticated_user=mock_authenticated_user,
        )

        mock_use_case.execute.assert_awaited_once_with(
            GetKeysCommand(user_id=None, offset=0, limit=10, sort_by=SortField.ID, sort_order=SortOrder.ASC, exclude_expired=False)
        )
