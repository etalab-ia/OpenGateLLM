from datetime import UTC, datetime
import json
import logging
from unittest.mock import ANY, create_autospec

from fastapi.exceptions import RequestValidationError
import pytest
from starlette.requests import Request

from api.domain.key.entities import Key
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.fastapi import RequestContext, RequestLogMiddleware, _requestlogmiddleware, record_http_exception, record_validation_exception
from api.infrastructure.fastapi.dependencies import request_context
from api.infrastructure.fastapi.endpoints.exceptions import OrganizationAlreadyExistsHTTPException


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
    user = AuthenticatedUserView(id=42, email="alice@example.com", name="Alice", organization_id=1, permissions=[], limits=[], expires=None)
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
    mock_logger.exception.assert_called_once_with("Unhandled exception while processing request", extra={**REQUEST_FIELDS, "error": "RuntimeError"})
    assert mock_logger.info.call_args.kwargs["extra"]["status_code"] == 500
    assert mock_logger.info.call_args.kwargs["extra"]["error"] == "RuntimeError"
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


@pytest.mark.asyncio
async def test_should_name_the_mapped_error_in_the_request_line():
    # Arrange
    request = Request({"type": "http", "method": "POST", "path": "/v1/admin/organizations", "headers": []})

    # Act
    response = await record_http_exception(request, OrganizationAlreadyExistsHTTPException("my-org"))

    # Assert
    assert request_context.get().error == "OrganizationAlreadyExistsHTTPException"
    assert response.status_code == 409
    assert json.loads(response.body) == {"detail": "Organization my-org already exists."}


@pytest.mark.asyncio
async def test_should_name_a_validation_error_in_the_request_line():
    # Arrange
    request = Request({"type": "http", "method": "POST", "path": "/v1/admin/organizations", "headers": []})

    # Act
    response = await record_validation_exception(request, RequestValidationError(errors=[]))

    # Assert
    assert request_context.get().error == "RequestValidationError"
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_should_report_the_unhandled_exception_to_sentry_as_a_crash(monkeypatch, mock_logger, send):
    # Arrange: swallowing the exception keeps it from SentryAsgiMiddleware, so the middleware must report it itself
    captured = []
    monkeypatch.setattr(_requestlogmiddleware.sentry_sdk, "capture_event", lambda event, hint: captured.append((event, hint)))
    error = RuntimeError("database is gone")

    async def failing_app(scope, receive, send):
        raise error

    # Act
    await RequestLogMiddleware(failing_app)(SCOPE, receive, send)

    # Assert
    ((event, hint),) = captured
    assert hint["exc_info"][1] is error
    assert event["exception"]["values"][-1]["mechanism"] == {"type": "asgi", "handled": False}
