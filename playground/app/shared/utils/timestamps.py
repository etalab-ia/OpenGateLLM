"""Timestamp helpers for the playground.

The OpenGateLLM API exposes every timestamp as Unix seconds in UTC (`created`, `updated`,
`expires`). The playground is the presentation layer: it renders those in the viewer's local
timezone, and converts local date-picker values back to Unix seconds when calling the API. Every
conversion goes through this module so it stays explicit — no naive `datetime.fromtimestamp(...)`
scattered per feature.

`astimezone()` without an argument resolves the system timezone *for the instant being converted*,
so the offset stays correct across DST boundaries.

See `adr/2026-08-27-datetime-handling.md`.
"""

import datetime as dt

DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M"


def local_now() -> dt.datetime:
    """Current time, as an aware datetime in the local timezone."""
    return dt.datetime.now(tz=dt.UTC).astimezone()


def to_local_datetime(timestamp: int | float | None) -> dt.datetime | None:
    """Convert a Unix timestamp (UTC seconds) to an aware datetime in the local timezone."""
    if timestamp is None:
        return None
    return dt.datetime.fromtimestamp(timestamp=timestamp, tz=dt.UTC).astimezone()


def format_datetime(timestamp: int | float | None, default: str = "") -> str:
    """Render a Unix timestamp as a local `YYYY-MM-DD HH:MM` string, or `default` if it is None."""
    local = to_local_datetime(timestamp)
    return default if local is None else local.strftime(DATETIME_FORMAT)


def format_date(timestamp: int | float | None, default: str = "") -> str:
    """Render a Unix timestamp as a local `YYYY-MM-DD` string, or `default` if it is None."""
    local = to_local_datetime(timestamp)
    return default if local is None else local.strftime(DATE_FORMAT)


def format_local_date(moment: dt.datetime) -> str:
    """Render a datetime as a local `YYYY-MM-DD` string, for date pickers."""
    return moment.astimezone().strftime(DATE_FORMAT)


def date_to_timestamp(date: str) -> int:
    """Convert a `YYYY-MM-DD` date picker value to Unix seconds, read as local midnight."""
    return int(dt.datetime.strptime(date, DATE_FORMAT).astimezone().timestamp())
