from datetime import UTC, datetime
import json
from logging import Filter, Formatter, LogRecord, StreamHandler, getLogger
from logging.config import dictConfig
import sys

from gunicorn.glogging import Logger as GunicornLogger
import yaml

from api.infrastructure.configuration import Settings
from api.infrastructure.fastapi.dependencies import request_context


class JsonFormatter(Formatter):
    RESERVED_ATTRIBUTES = frozenset(vars(LogRecord("", 0, "", 0, "", None, None))) | {"message", "asctime", "color_message"}

    def format(self, record):
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "process": record.process,
            "message": record.getMessage(),
        }
        payload.update({key: value for key, value in vars(record).items() if key not in self.RESERVED_ATTRIBUTES})
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)

        return json.dumps(payload, default=str, ensure_ascii=False)


class RequestIdFilter(Filter):
    def filter(self, record):
        if (request_id := request_context.get().id) is not None:
            record.request_id = request_id
        return True


class JsonGunicornLogger(GunicornLogger):
    def setup(self, cfg):
        super().setup(cfg)
        for handler in self.error_log.handlers + self.access_log.handlers:
            handler.setFormatter(JsonFormatter())


def configure_logging(settings: Settings) -> None:
    if settings.log_config:
        _apply_log_config_file(settings.log_config)
        return

    logger = getLogger(name="api")
    logger.setLevel(level=settings.log_level)
    handler = StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIdFilter())

    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False

    getLogger(name="uvicorn.access").disabled = True

    for uvicorn_handler in getLogger(name="uvicorn").handlers + getLogger(name="uvicorn.error").handlers:
        uvicorn_handler.setFormatter(JsonFormatter())


def _apply_log_config_file(path: str) -> None:
    with open(path) as file:
        config = yaml.safe_load(file)
    config.setdefault("disable_existing_loggers", False)
    dictConfig(config)
