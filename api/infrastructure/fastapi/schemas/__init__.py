from datetime import datetime
from typing import Annotated

from pydantic import BeforeValidator


def _to_unix_timestamp(value: datetime | int) -> int:
    return int(value.timestamp()) if isinstance(value, datetime) else value


UnixTimestamp = Annotated[int, BeforeValidator(_to_unix_timestamp)]

MIN_PASSWORD_LENGTH: int = 6
MAX_PASSWORD_LENGTH: int = 72

__all__ = ["MAX_PASSWORD_LENGTH", "MIN_PASSWORD_LENGTH", "UnixTimestamp"]
