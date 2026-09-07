from datetime import datetime
from typing import Annotated

from pydantic import BeforeValidator


def _to_unix_timestamp(value: datetime | int) -> int:
    return int(value.timestamp()) if isinstance(value, datetime) else value


UnixTimestamp = Annotated[int, BeforeValidator(_to_unix_timestamp)]

__all__ = ["UnixTimestamp"]
