from datetime import datetime
from typing import Annotated

from pydantic import BeforeValidator


def _to_unix_timestamp(value: datetime | int) -> int:
    return int(value.timestamp()) if isinstance(value, datetime) else value


UnixTimestamp = Annotated[int, BeforeValidator(_to_unix_timestamp)]

MIN_PASSWORD_LENGTH: int = 6
MAX_PASSWORD_BYTES: int = 72


def reject_password_over_max_bytes(value: str | None) -> str | None:
    """Reject a password whose UTF-8 encoding exceeds what bcrypt can hash (72 bytes)."""
    if value is not None and len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes long.")
    return value


__all__ = ["MAX_PASSWORD_BYTES", "MIN_PASSWORD_LENGTH", "UnixTimestamp", "reject_password_over_max_bytes"]
