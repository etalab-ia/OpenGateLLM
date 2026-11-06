from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from app.features.auth.state import AuthState


@pytest.mark.asyncio
async def test_should_reload_authenticated_page_to_run_on_load_handlers():
    # Arrange
    state = SimpleNamespace(email_input="demo@example.fr", password_input="password", is_loading=False)
    state._apply_session = lambda **kwargs: None
    login_response = httpx.Response(200, json={"id": 1, "value": "key", "expires": None}, request=httpx.Request("POST", "http://localhost"))
    user_response = httpx.Response(200, json={"id": 7}, request=httpx.Request("GET", "http://localhost"))
    state._password_login = AsyncMock(return_value=login_response)
    state._get_user_info = AsyncMock(return_value=user_response)

    # Act
    events = [event async for event in AuthState.basic_login.fn(state)]

    # Assert
    reload_events = [event for event in events if hasattr(event, "args")]
    assert any(getattr(argument, "_var_value", None) == "window.location.reload()" for event in reload_events for _, argument in event.args)
    assert state.is_loading is False
