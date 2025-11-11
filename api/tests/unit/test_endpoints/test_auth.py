import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.endpoints.auth import login
from api.schemas.auth import Login, LoginResponse
from api.utils.context import global_context
from api.utils.exceptions import InvalidPasswordException


class MockIdentityAccessManagerSuccess:
    LOGIN_KEY_ID = 7
    LOGIN_KEY = "sk-test-token"

    async def login(self, session, email, password):
        return self.LOGIN_KEY_ID, self.LOGIN_KEY


class MockIdentityAccessManagerFail:
    async def login(self, session, email, password):
        raise InvalidPasswordException


@pytest.mark.asyncio
async def test_login_success():
    """Test successful login returns correct token and id"""
    # Mock dependencies
    global_context.identity_access_manager = MockIdentityAccessManagerSuccess()
    mock_request = MagicMock()
    mock_session = AsyncMock()

    # Create login body
    body = Login(email="user@example.com", password="secret")

    # Call endpoint directly
    response = await login(request=mock_request, body=body, session=mock_session)

    # Verify response
    assert response.status_code == 200
    response_data = json.loads(response.body.decode())
    data = LoginResponse(**response_data)
    assert data.key == MockIdentityAccessManagerSuccess.LOGIN_KEY
    assert data.id == MockIdentityAccessManagerSuccess.LOGIN_KEY_ID


@pytest.mark.asyncio
async def test_login_invalid_credentials():
    """Test login with invalid credentials raises exception"""
    # Mock dependencies
    global_context.identity_access_manager = MockIdentityAccessManagerFail()
    mock_request = MagicMock()
    mock_session = AsyncMock()

    # Create login body
    body = Login(email="user@example.com", password="wrong")

    # Call endpoint and expect exception
    with pytest.raises(InvalidPasswordException):
        await login(request=mock_request, body=body, session=mock_session)
