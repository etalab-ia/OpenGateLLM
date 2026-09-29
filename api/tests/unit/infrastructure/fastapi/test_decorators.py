import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from api.domain.key.entities import Key
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.fastapi import RequestContext
from api.infrastructure.fastapi.decorators import cancel_on_disconnect
from api.infrastructure.fastapi.dependencies import request_context

ROUTER_ID = 3


def _authenticated_user() -> AuthenticatedUserView:
    return AuthenticatedUserView(
        id=42,
        email="alice@example.com",
        name="Alice",
        organization_id=1,
        budget=10.0,
        permissions=[],
        limits=[],
        expires=None,
    )


def _set_request_context(**overrides) -> None:
    now = datetime.now(tz=UTC)
    context = RequestContext(
        endpoint="/v1/ocr",
        key=Key(id=7, name="my-key", user_id=42, value="sk-...", expires=None, created=now),
        user=_authenticated_user(),
        router_id=ROUTER_ID,
        provider_id=8,
        router_name="ocr-router",
        provider_model_name="ocr-provider",
        **overrides,
    )
    request_context.set(context)


@pytest.fixture(autouse=True)
def reset_request_context():
    token = request_context.set(RequestContext())
    yield
    request_context.reset(token)


class TestCancelOnDisconnect:
    @pytest.mark.asyncio
    async def test_should_cancel_endpoint_task(self):
        # Arrange
        cancelled = False
        started = asyncio.Event()

        @cancel_on_disconnect
        async def endpoint(request):
            nonlocal cancelled
            try:
                started.set()
                await asyncio.Event().wait()
            finally:
                cancelled = True

        async def is_disconnected():
            await started.wait()
            return True

        request = SimpleNamespace(
            url=SimpleNamespace(path="/v1/ocr"),
            is_disconnected=AsyncMock(side_effect=is_disconnected),
        )

        # Act
        with pytest.raises(asyncio.CancelledError):
            await endpoint(request=request)

        # Assert
        assert cancelled is True
