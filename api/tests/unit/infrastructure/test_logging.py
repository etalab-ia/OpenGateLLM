import json
import logging

from gunicorn.config import Config as GunicornConfig
import pytest

from api.infrastructure.configuration import get_configuration
from api.infrastructure.logging import JsonGunicornLogger, configure_logging


@pytest.fixture
def settings():
    return get_configuration().settings.model_copy(update={"log_level": "INFO", "log_format": "%(levelname)s|%(name)s|%(message)s"})


@pytest.fixture(autouse=True)
def restore_api_logger():
    api_logger = logging.getLogger("api")
    handlers, level, propagate = list(api_logger.handlers), api_logger.level, api_logger.propagate
    yield
    api_logger.handlers, api_logger.level, api_logger.propagate = handlers, level, propagate


def test_should_emit_info_logs_of_any_api_module_with_configured_format(settings, capsys):
    # Arrange
    configure_logging(settings)

    # Act
    logging.getLogger("api.infrastructure.fastapi.endpoints.keys").info("hello")

    # Assert
    output = capsys.readouterr().out
    assert "INFO" in output
    assert "|api.infrastructure.fastapi.endpoints.keys|hello" in output


def test_should_not_stack_handlers_when_configured_twice(settings):
    # Arrange
    configure_logging(settings)

    # Act
    configure_logging(settings)

    # Assert
    assert len(logging.getLogger("api").handlers) == 1


def test_should_emit_one_json_object_per_line_with_extra_fields_when_json_is_enabled(settings, capsys):
    # Arrange
    configure_logging(settings.model_copy(update={"log_json": True}))

    # Act
    logging.getLogger("api.infrastructure.fastapi.endpoints.keys").info("hello %s", "world", extra={"authenticated_user_id": 42})

    # Assert
    record = json.loads(capsys.readouterr().out)
    assert record["level"] == "INFO"
    assert record["logger"] == "api.infrastructure.fastapi.endpoints.keys"
    assert record["message"] == "hello world"
    assert record["authenticated_user_id"] == 42
    assert "exception" not in record


def test_should_include_traceback_in_json_when_logging_an_exception(settings, capsys):
    # Arrange
    configure_logging(settings.model_copy(update={"log_json": True}))

    # Act
    try:
        raise ValueError("boom")
    except ValueError:
        logging.getLogger("api.lifespan").exception("failed")

    # Assert
    record = json.loads(capsys.readouterr().out)
    assert record["level"] == "ERROR"
    assert "ValueError: boom" in record["exception"]


def test_should_render_gunicorn_error_and_access_logs_as_json(capsys):
    # Arrange
    config = GunicornConfig()
    config.set("accesslog", "-")
    gunicorn_logger = JsonGunicornLogger(config)

    # Act
    gunicorn_logger.error_log.info("Booting worker")
    gunicorn_logger.access_log.info("GET /health")

    # Assert
    output = capsys.readouterr()
    assert json.loads(output.err)["message"] == "Booting worker"
    assert json.loads(output.out)["logger"] == "gunicorn.access"


def test_should_render_uvicorn_access_fields_as_json_keys(capsys):
    # Arrange
    config = GunicornConfig()
    config.set("accesslog", "-")
    gunicorn_logger = JsonGunicornLogger(config)
    uvicorn_access_log = logging.getLogger("uvicorn.access")
    uvicorn_access_log.handlers = gunicorn_logger.access_log.handlers
    uvicorn_access_log.setLevel(gunicorn_logger.access_log.level)
    uvicorn_access_log.propagate = False

    # Act
    uvicorn_access_log.info('%s - "%s %s HTTP/%s" %d', "127.0.0.1:42564", "POST", "/v1/chat/completions?x=1", "1.1", 429)

    # Assert
    record = json.loads(capsys.readouterr().out)
    assert record["method"] == "POST"
    assert record["path"] == "/v1/chat/completions?x=1"
    assert record["status_code"] == 429
