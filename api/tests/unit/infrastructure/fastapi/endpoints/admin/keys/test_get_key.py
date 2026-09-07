from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.domain.key.entities import Key
from api.domain.key.errors import KeyNotFoundError
from api.infrastructure.fastapi.endpoints.admin.keys import get_key
from api.infrastructure.fastapi.endpoints.exceptions import KeyNotFoundHTTPException
from api.infrastructure.fastapi.schemas.admin.keys import KeyResponse
from api.use_cases.admin.keys import GetOneKeyCommand, GetOneKeyUseCaseSuccess


@pytest.fixture
def mock_authenticated_user():
    return MagicMock(id=1)


class TestGetKeyEndpoint:
    @pytest.mark.asyncio
    async def test_should_map_key_to_key_response(self, mock_authenticated_user):
        key = Key(
            id=1,
            name="my-key",
            user_id=42,
            value="sk-masked...value",
            expires=None,
            created=datetime(2030, 1, 1, tzinfo=UTC),
        )
        mock_use_case = MagicMock()
        mock_use_case.execute = AsyncMock(return_value=GetOneKeyUseCaseSuccess(key=key))

        result = await get_key(key_id=1, get_one_key_use_case=mock_use_case, authenticated_user=mock_authenticated_user)

        assert isinstance(result, KeyResponse)
        assert result.id == 1
        assert result.name == "my-key"
        assert result.user_id == 42
        mock_use_case.execute.assert_awaited_once_with(GetOneKeyCommand(key_id=1))

    @pytest.mark.asyncio
    async def test_should_raise_key_not_found_http_exception(self, mock_authenticated_user):
        mock_use_case = MagicMock()
        mock_use_case.execute = AsyncMock(return_value=KeyNotFoundError(id=99))

        with pytest.raises(KeyNotFoundHTTPException) as exc_info:
            await get_key(key_id=99, get_one_key_use_case=mock_use_case, authenticated_user=mock_authenticated_user)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Key 99 not found."
