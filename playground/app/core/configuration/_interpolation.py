import os
import re
from typing import Any

from pydantic import model_validator

from ._validationerrors import HiddenInputSchema, _nested_schema

VARIABLE_REFERENCE_PATTERN = re.compile(r"\$\{([^}]*?)(:-[^}]*)?\}")
VARIABLE_NAME_PATTERN = re.compile(r"[A-Z0-9_]+")


class ConfigurationVariableError(Exception):
    """Not a ValueError: Pydantic would wrap it in a ValidationError, and bury the message."""


class ConfigBaseModel(HiddenInputSchema):
    @model_validator(mode="before")
    @classmethod
    def interpolate_own_fields(cls, data: Any) -> Any:
        """
        A value is interpolated by the model that validates it, so a ${VAR} under a key no loaded model declares is left as it is. That is what
        lets the frontend build validate CompiledConfigFile without the variables only the container entrypoint reads.
        """
        if not isinstance(data, dict):
            return data

        return {key: interpolate_variables(value) if cls._owns(key) else value for key, value in data.items()}

    @classmethod
    def _owns(cls, key: str) -> bool:
        field = cls.__pydantic_fields__.get(key)
        if field is None:  # an extra: a key of the other application, which this model never reads
            return False

        # A nested model owns its subtree: resolving it here would also resolve the keys that model leaves out.
        return _nested_schema(field.annotation) is None


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
