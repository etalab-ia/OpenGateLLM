import json
import logging
from logging.config import dictConfig
from pathlib import Path

from gunicorn.config import Config as GunicornConfig
import pytest
from uvicorn.config import LOGGING_CONFIG as UVICORN_LOGGING_CONFIG

from api.infrastructure.configuration import get_configuration
from api.infrastructure.fastapi import RequestContext
from api.infrastructure.fastapi.dependencies import request_context
from api.infrastructure.logging import JsonGunicornLogger, configure_logging

EXAMPLE_LOG_CONFIG = Path(__file__).parents[4] / "logging.example.yml"


@pytest.fixture
def settings():
    return get_configuration().settings.model_copy(
        update={"log_level": "INFO", "log_format": "%(levelname)s|%(name)s|%(message)s", "log_json": False, "log_config": None}
    )


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


@pytest.fixture
def restore_uvicorn_loggers():
    loggers = [logging.getLogger(name) for name in ("uvicorn", "uvicorn.error", "uvicorn.access")]
    states = [(list(logger.handlers), logger.level, logger.propagate, logger.disabled) for logger in loggers]
    yield
    for logger, (handlers, level, propagate, disabled) in zip(loggers, states):
        logger.handlers, logger.level, logger.propagate, logger.disabled = handlers, level, propagate, disabled


def test_should_render_standalone_uvicorn_logs_as_json_when_json_is_enabled(settings, restore_uvicorn_loggers, capsys):
    # Arrange
    # In the test body: dictConfig binds the handlers to the sys.stdout / sys.stderr that capsys swaps in for the call phase.
    dictConfig(UVICORN_LOGGING_CONFIG)
    configure_logging(settings.model_copy(update={"log_json": True}))

    # Act
    logging.getLogger("uvicorn.error").info("Started server process")

    # Assert
    assert json.loads(capsys.readouterr().err)["message"] == "Started server process"


def test_should_disable_uvicorn_access_log_replaced_by_the_request_log(settings, restore_uvicorn_loggers, capsys):
    # Arrange
    dictConfig(UVICORN_LOGGING_CONFIG)
    configure_logging(settings)

    # Act
    logging.getLogger("uvicorn.access").info('%s - "%s %s HTTP/%s" %d', "127.0.0.1:42564", "GET", "/health", "1.1", 200)

    # Assert
    assert capsys.readouterr().out == ""


def test_should_add_the_request_id_to_api_logs_during_a_request(settings, capsys):
    # Arrange
    configure_logging(settings.model_copy(update={"log_json": True}))
    token = request_context.set(RequestContext(id="3f2a"))

    # Act
    try:
        logging.getLogger("api.infrastructure.http._httpproviderclient").error("provider unreachable")
    finally:
        request_context.reset(token)

    # Assert
    assert json.loads(capsys.readouterr().out)["request_id"] == "3f2a"


def test_should_apply_the_example_log_config_file(settings, restore_uvicorn_loggers, capsys):
    # Arrange
    configure_logging(settings.model_copy(update={"log_config": str(EXAMPLE_LOG_CONFIG)}))
    token = request_context.set(RequestContext(id="3f2a"))

    # Act
    try:
        logging.getLogger("api.infrastructure.http._httpproviderclient").info("provider selected")
        logging.getLogger("uvicorn.access").info('%s - "%s %s HTTP/%s" %d', "127.0.0.1:42564", "GET", "/health", "1.1", 200)
    finally:
        request_context.reset(token)

    # Assert
    record = json.loads(capsys.readouterr().out)
    assert record["message"] == "provider selected"
    assert record["request_id"] == "3f2a"


def test_should_keep_module_loggers_enabled_when_the_log_config_file_omits_disable_existing_loggers(settings, tmp_path):
    # Arrange
    module_logger = logging.getLogger("api.infrastructure.redis._redisrouterratelimiter")
    log_config = tmp_path / "logging.yml"
    log_config.write_text("version: 1\nloggers:\n  api:\n    level: WARNING\n")

    # Act
    configure_logging(settings.model_copy(update={"log_config": str(log_config)}))

    # Assert
    assert not module_logger.disabled
    assert logging.getLogger("api").level == logging.WARNING
