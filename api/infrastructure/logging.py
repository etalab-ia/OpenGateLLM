from contextvars import ContextVar
from logging import Filter, Formatter, Handler, Logger, StreamHandler, getLogger
import sys

from uvicorn.logging import AccessFormatter

from api.infrastructure.configuration import configuration

client_ip: ContextVar[str | None] = ContextVar("client_ip", default=None)


class ClientIPFilter(Filter):
    def filter(self, record):
        client_addr = client_ip.get()
        record.client_ip = client_addr if client_addr else "."
        return True


class RequestIdFilter(Filter):
    def filter(self, record):
        from api.infrastructure.fastapi.dependencies import request_context

        record.request_id = request_context.get().id or "-"
        return True


class ColoredFormatter(Formatter):
    """Custom formatter with colors for different log levels"""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def _ensure_context_filters(handler: Handler) -> None:
    if not any(isinstance(f, ClientIPFilter) for f in handler.filters):
        handler.addFilter(ClientIPFilter())
    if not any(isinstance(f, RequestIdFilter) for f in handler.filters):
        handler.addFilter(RequestIdFilter())


def _apply_formatter(logger: Logger, formatter: Formatter) -> None:
    for handler in logger.handlers:
        handler.setFormatter(formatter)
        _ensure_context_filters(handler)


def configure_logging() -> None:
    """Configure the `api` logger and uvicorn loggers.

    Safe to call more than once: the `api` logger is set up only the first time;
    uvicorn handlers are re-applied because they may appear after create_app.

    Under plain uvicorn, server lines live on `uvicorn` (via propagation from
    `uvicorn.error`). Under gunicorn + UvicornWorker, handlers are attached
    directly to `uvicorn.error` with propagate=False — both must be formatted.
    """
    logger = getLogger("api")
    if not logger.handlers:
        logger.setLevel(level=configuration.settings.log_level)
        handler = StreamHandler(stream=sys.stdout)
        handler.setFormatter(ColoredFormatter(configuration.settings.log_format))
        _ensure_context_filters(handler)
        logger.addHandler(handler)
        logger.propagate = False

    app_formatter = ColoredFormatter(configuration.settings.log_format)
    _apply_formatter(getLogger("uvicorn"), app_formatter)
    _apply_formatter(getLogger("uvicorn.error"), app_formatter)
    _apply_formatter(getLogger("uvicorn.access"), AccessFormatter(fmt=configuration.settings.access_log_format))
