import os
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field, field_validator
import yaml

from ._interpolation import interpolate_variables
from ._validationerrors import HiddenInputSchema, custom_validation_error
from .sections import Dependencies, Model, PostgresDependency, SettingsLoginOIDC, SettingsLoginPassword

DEFAULT_CONFIG_FILE = "config.yml"


def get_configuration(config_file: str | None = None) -> "Configuration":
    config_file = config_file or os.getenv("CONFIG_FILE", DEFAULT_CONFIG_FILE)
    if not Path(config_file).is_file():
        raise FileNotFoundError(f"Config file ({config_file}) not found.")

    return Configuration(**interpolate_variables(read_config_file(path=config_file)))


def get_postgres_dependency() -> PostgresDependency:
    raw_config = read_config_file(path=os.getenv("CONFIG_FILE", DEFAULT_CONFIG_FILE))
    return PostgresDependency(**interpolate_variables(raw_config["dependencies"]["postgres"]))


@custom_validation_error
class Configuration(HiddenInputSchema):
    """
    Configuration file is composed of 3 sections, models:
    - `models`: to declare models API exposed to the API.
    - `dependencies`: to declare both required plugins for the API (e.g. PostgreSQL, Redis) and optional ones (e.g. Sentry).
    - `settings`: to configure the API.

    :::warnings
    We don't recommend to use the configuration file to declare models, prefer to use the API to declare models, by endpoints or on the Playground UI (see [Models configuration](/getting-started/models/)).
    :::
    """

    models: list[Model] = Field(default_factory=list, description="Models used by the API.")  # fmt: off
    dependencies: Dependencies = Field(default_factory=Dependencies, description="Dependencies required by the applications (API and Playground).")  # fmt: off
    settings: Annotated[SettingsLoginPassword | SettingsLoginOIDC, Field(discriminator="auth_login_type", default_factory=SettingsLoginPassword, description="General settings configuration fields.")]  # fmt: off

    @field_validator("settings", mode="before")
    def set_default_login_type(cls, settings) -> Any:
        if settings is None:
            return SettingsLoginPassword()
        elif isinstance(settings, dict):
            settings.setdefault("auth_login_type", "password")
            return settings
        return settings


def read_config_file(path: str) -> dict:
    with open(file=path) as file:
        return yaml.safe_load(stream=file)
