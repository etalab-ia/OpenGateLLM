from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock

from fastapi import HTTPException
import pytest

from api.domain.key.entities import Key
from api.domain.usage.entities import EnvironmentalImpacts
from api.domain.usage.entities import Usage as RecordedUsage
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.fastapi import RequestContext, decorators
from api.infrastructure.fastapi.decorators import _wrap_streaming_response, hooks, set_usage_from_context
from api.infrastructure.fastapi.dependencies import request_context
from api.infrastructure.postgres.models import Usage

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


class TestWrapStreamingResponse:
    @pytest.mark.asyncio
    async def test_should_record_the_usage_row_even_when_closing_the_stream_fails(self):
        """The row is the billing record: whatever goes wrong while draining the chain, it has to be written."""
        # Arrange
        recorded: list[Usage] = []

        async def failing_stream() -> AsyncGenerator:
            try:
                yield ("data: hello\n\n", 200)
            finally:
                raise RuntimeError("cleanup blew up")

        response = _wrap_streaming_response(
            response=AsyncMock(body_iterator=failing_stream(), media_type="text/event-stream", headers={}),
            usage=Usage(endpoint="/v1/chat/completions"),
            record=lambda usage: recorded.append(usage),
        )

        # Act: read one chunk, then abandon the stream as a disconnecting client does
        await response.body_iterator.__anext__()
        with pytest.raises(RuntimeError):
            await response.body_iterator.aclose()

        # Assert
        assert len(recorded) == 1, "a failure while closing the chain must not swallow the usage row"


class TestSetUsageFromContext:
    def test_should_carry_the_user_and_cost_into_the_row(self):
        # Arrange
        _set_request_context(
            usage=RecordedUsage(
                prompt_tokens=7,
                completion_tokens=3,
                total_tokens=10,
                cost=0.02,
                impacts=EnvironmentalImpacts(kWh=1.5, kgCO2eq=2.5),
            )
        )

        # Act
        usage = set_usage_from_context(usage=Usage())

        # Assert
        assert usage.user_id == 42
        assert usage.cost == 0.02

    def test_should_leave_the_cost_none_when_nothing_was_recorded(self):
        # Arrange: the request failed before the provider was called
        _set_request_context()

        # Act
        usage = set_usage_from_context(usage=Usage())

        # Assert
        assert usage.cost is None


class TestHooksRecordedStatus:
    @staticmethod
    def _decorated(endpoint_func):
        return hooks(postgres_session_provider=AsyncMock())(endpoint_func)

    @pytest.mark.asyncio
    async def test_should_record_the_status_of_a_mapped_http_exception(self, monkeypatch):
        # Arrange
        recorded: list[RecordedUsage] = []
        monkeypatch.setattr(decorators, "_record_usage", lambda usage, postgres_session_provider: recorded.append(usage))
        _set_request_context()

        async def endpoint():
            raise HTTPException(status_code=409, detail="already exists")

        # Act
        with pytest.raises(HTTPException):
            await self._decorated(endpoint)()

        # Assert
        assert [usage.status for usage in recorded] == [409]

    @pytest.mark.asyncio
    async def test_should_record_500_when_the_endpoint_raises_an_unexpected_exception(self, monkeypatch):
        # Arrange: RequestLogMiddleware answers 500, so the usage row must carry it too
        recorded: list[RecordedUsage] = []
        monkeypatch.setattr(decorators, "_record_usage", lambda usage, postgres_session_provider: recorded.append(usage))
        _set_request_context()

        async def endpoint():
            raise RuntimeError("database is gone")

        # Act
        with pytest.raises(RuntimeError):
            await self._decorated(endpoint)()

        # Assert
        assert [usage.status for usage in recorded] == [500]
