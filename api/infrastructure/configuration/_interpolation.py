import os
import re
from typing import Any

VARIABLE_REFERENCE_PATTERN = re.compile(r"\$\{([^}]*?)(:-[^}]*)?\}")
VARIABLE_NAME_PATTERN = re.compile(r"[A-Z0-9_]+")


class ConfigurationVariableError(Exception):
    """Not a ValueError: Pydantic would wrap it in a ValidationError, and bury the message."""


def interpolate_variables(value: Any) -> Any:
    match value:
        case str():
            return VARIABLE_REFERENCE_PATTERN.sub(_get_variable_value, value)
        case dict():
            return {key: interpolate_variables(item) for key, item in value.items()}
        case list():
            return [interpolate_variables(item) for item in value]
        case _:
            return value


def _get_variable_value(match: re.Match) -> str:
    name, default = match.groups()
    if not VARIABLE_NAME_PATTERN.fullmatch(name):
        raise ConfigurationVariableError(f"Invalid environment variable name in the configuration file: {name!r}. A name only holds A-Z, 0-9 and _.")

    value = os.getenv(name)
    if value:
        return value
    if default is not None:
        return default.removeprefix(":-")

    raise ConfigurationVariableError(f"Environment variable {name} of the configuration file is missing or empty, and has no default.")
