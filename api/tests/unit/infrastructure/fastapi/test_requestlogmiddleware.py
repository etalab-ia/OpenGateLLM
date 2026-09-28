from datetime import UTC, datetime
import json
import logging
from unittest.mock import ANY, create_autospec

import pytest

from api.domain.key.entities import Key
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.fastapi import RequestContext, RequestLogMiddleware, _requestlogmiddleware
from api.infrastructure.fastapi.dependencies import request_context


async def get_organization():
    pass


SCOPE = {
    "type": "http",
    "method": "GET",
    "path": "/v1/admin/organizations/7",
    "endpoint": get_organization,
    "path_params": {"organization_id": 7},
    "client": ("10.0.0.1", 42564),
}
REQUEST_FIELDS = {
    "method": "GET",
    "path": "/v1/admin/organizations/7",
    "handler": f"{__name__}.get_organization",
    "path_params": {"organization_id": 7},
    "client_addr": "10.0.0.1",
    "authenticated_user_id": 42,
    "key_id": 5,
    "router_name": "my-router",
}


@pytest.fixture
def mock_logger(monkeypatch):
    mock_logger = create_autospec(logging.Logger, instance=True, spec_set=True)
    monkeypatch.setattr(_requestlogmiddleware, "logger", mock_logger)
    return mock_logger


@pytest.fixture(autouse=True)
def authenticated_request_context():
    user = AuthenticatedUserView(
        id=42, email="alice@example.com", name="Alice", organization_id=1, budget=None, permissions=[], limits=[], expires=None
    )
    key = Key(id=5, name="my-key", user_id=42, value="sk-...", expires=None, created=datetime.now(tz=UTC))
    token = request_context.set(RequestContext(id="3f2a", user=user, key=key, router_name="my-router"))
    yield
    request_context.reset(token)


@pytest.fixture
def sent_messages():
    return []


@pytest.fixture
def send(sent_messages):
    async def send(message):
        sent_messages.append(message)

    return send


async def receive():
    return {"type": "http.request", "body": b""}


@pytest.mark.asyncio
async def test_should_log_one_line_with_the_request_context_when_the_app_answers(mock_logger, send):
    # Arrange
    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 201, "headers": []})
        await send({"type": "http.response.body", "body": b"{}"})

    # Act
    await RequestLogMiddleware(app)(SCOPE, receive, send)

    # Assert
    mock_logger.info.assert_called_once_with(
        "%s %s %s %.1fms",
        "GET",
        "/v1/admin/organizations/7",
        201,
        ANY,
        extra={**REQUEST_FIELDS, "status_code": 201, "duration_ms": ANY},
    )
    mock_logger.exception.assert_not_called()


@pytest.mark.asyncio
async def test_should_log_the_exception_and_answer_generic_500_when_the_app_raises(mock_logger, send, sent_messages):
    # Arrange
    async def failing_app(scope, receive, send):
        raise RuntimeError("database is gone")

    # Act
    await RequestLogMiddleware(failing_app)(SCOPE, receive, send)

    # Assert
    mock_logger.exception.assert_called_once_with("Unhandled exception while processing request", extra=REQUEST_FIELDS)
    assert mock_logger.info.call_args.kwargs["extra"]["status_code"] == 500
    assert sent_messages[0]["status"] == 500
    assert json.loads(sent_messages[1]["body"]) == {"detail": "An unexpected error occurred"}


@pytest.mark.asyncio
async def test_should_reraise_and_still_log_the_request_when_the_response_has_already_started(mock_logger, send, sent_messages):
    # Arrange
    async def app_failing_mid_response(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        raise RuntimeError("provider stream broke")

    # Act / Assert
    with pytest.raises(RuntimeError):
        await RequestLogMiddleware(app_failing_mid_response)(SCOPE, receive, send)
    mock_logger.exception.assert_not_called()
    assert mock_logger.info.call_args.kwargs["extra"]["status_code"] == 200
    assert [message["type"] for message in sent_messages] == ["http.response.start"]


@pytest.mark.asyncio
async def test_should_leave_out_the_fields_that_do_not_apply_to_the_route(mock_logger, send):
    # Arrange
    token = request_context.set(RequestContext(id="9c1e"))

    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})

    # Act
    try:
        await RequestLogMiddleware(app)({"type": "http", "method": "GET", "path": "/health", "path_params": {}, "client": None}, receive, send)
    finally:
        request_context.reset(token)

    # Assert
    assert mock_logger.info.call_args.kwargs["extra"] == {"method": "GET", "path": "/health", "status_code": 200, "duration_ms": ANY}
