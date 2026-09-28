from contextvars import ContextVar
from datetime import UTC, datetime
import json
from logging import Filter, Formatter, LogRecord, StreamHandler, getLogger
import sys

from gunicorn.glogging import Logger as GunicornLogger

from api.infrastructure.configuration import Settings

client_ip: ContextVar[str | None] = ContextVar("client_ip", default=None)


class ClientIPFilter(Filter):
    def filter(self, record):
        client_addr = client_ip.get()
        record.client_ip = client_addr if client_addr else "."
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


class JsonFormatter(Formatter):
    """One JSON object per line; the `extra={...}` passed to a log call become top-level keys."""

    # color_message: uvicorn duplicates its message with ANSI codes for its own colored formatter.
    RESERVED_ATTRIBUTES = frozenset(vars(LogRecord("", 0, "", 0, "", None, None))) | {"message", "asctime", "client_ip", "color_message"}

    def format(self, record):
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "process": record.process,
            "message": record.getMessage(),
        }
        if address := client_ip.get():
            payload["client_ip"] = address
        payload.update({key: value for key, value in vars(record).items() if key not in self.RESERVED_ATTRIBUTES})
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)

        # default=str: an extra value that JSON cannot encode (UUID, datetime, entity…) must not drop the log line.
        return json.dumps(payload, default=str, ensure_ascii=False)


class UvicornAccessFieldsFilter(Filter):
    """Exposes the fields of a uvicorn access log as record attributes, so JsonFormatter renders them as JSON keys."""

    def filter(self, record):
        # uvicorn logs every access with the args (client_addr, method, path_with_query, http_version, status_code).
        if record.name == "uvicorn.access" and isinstance(record.args, tuple) and len(record.args) == 5:
            _, record.method, record.path, _, record.status_code = record.args
        return True


class JsonGunicornLogger(GunicornLogger):
    """gunicorn logger rendering JSON. UvicornWorker reuses its handlers for uvicorn.error and uvicorn.access."""

    def setup(self, cfg):
        # Only the rendering changes: gunicorn keeps deciding which handlers exist (errorlog, accesslog, syslog, --log-config).
        super().setup(cfg)
        for handler in self.error_log.handlers + self.access_log.handlers:
            handler.setFormatter(JsonFormatter())
        # UvicornWorker hands these handlers to uvicorn.access; gunicorn's own access records are skipped by the filter.
        for handler in self.access_log.handlers:
            handler.addFilter(UvicornAccessFieldsFilter())


def configure_logging(settings: Settings) -> None:
    # Every module logs through getLogger(__name__), so configuring the "api" parent covers the whole application.
    logger = getLogger(name="api")
    logger.setLevel(level=settings.log_level)
    handler = StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonFormatter() if settings.log_json else ColoredFormatter(settings.log_format))
    handler.addFilter(ClientIPFilter())

    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False  # Prevent propagation to root logger
