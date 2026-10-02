import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from api.infrastructure.fastapi.decorators import cancel_on_disconnect


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
