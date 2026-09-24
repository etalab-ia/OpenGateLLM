from io import StringIO
import logging

from api.infrastructure.logging import ColoredFormatter, configure_logging


def test_should_configure_api_logger_once_so_child_loggers_propagate():
    # Arrange
    api_logger = logging.getLogger("api")
    api_logger.handlers.clear()

    # Act
    configure_logging()
    configure_logging()

    # Assert
    assert len(api_logger.handlers) == 1
    assert api_logger.propagate is False
    child = logging.getLogger("api.infrastructure.fastapi.accesscontroller")
    assert child.getEffectiveLevel() == api_logger.level


def test_should_format_uvicorn_error_when_handlers_live_on_parent():
    # Arrange — plain uvicorn: records on uvicorn.error, handlers on uvicorn
    stream = StringIO()
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers.clear()
    uvicorn_logger.setLevel(logging.INFO)
    uvicorn_logger.propagate = False
    uvicorn_logger.addHandler(logging.StreamHandler(stream))
    logging.getLogger("uvicorn.error").handlers.clear()
    logging.getLogger("uvicorn.error").propagate = True

    # Act
    configure_logging()
    logging.getLogger("uvicorn.error").info("Waiting for application startup.")

    # Assert
    assert isinstance(uvicorn_logger.handlers[0].formatter, ColoredFormatter)
    assert "Waiting for application startup." in stream.getvalue()
    assert "client_ip" in stream.getvalue()


def test_should_format_uvicorn_error_when_handlers_live_on_error_logger():
    # Arrange — gunicorn + UvicornWorker: handlers on uvicorn.error, no propagate
    stream = StringIO()
    error_logger = logging.getLogger("uvicorn.error")
    error_logger.handlers.clear()
    error_logger.setLevel(logging.INFO)
    error_logger.propagate = False
    error_logger.addHandler(logging.StreamHandler(stream))

    # Act
    configure_logging()
    error_logger.info("Started server process [1]")

    # Assert
    assert isinstance(error_logger.handlers[0].formatter, ColoredFormatter)
    assert "Started server process [1]" in stream.getvalue()
    assert "client_ip" in stream.getvalue()
