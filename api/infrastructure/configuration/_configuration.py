from functools import lru_cache
import os
from pathlib import Path
from typing import Annotated, Any

from pydantic import ConfigDict, Field, field_validator, model_validator
from pydantic_settings import BaseSettings
import yaml

from ._interpolation import interpolate_variables
from ._validationerrors import HiddenInputSchema, custom_validation_error
from .sections import Dependencies, Model, PostgresDependency, SettingsLoginOIDC, SettingsLoginPassword


@lru_cache
def get_configuration() -> "Configuration":
    return Configuration()


def get_postgres_dependency() -> PostgresDependency:
    raw_config = read_config_file(path=os.getenv("CONFIG_FILE", "config.yml"))
    return PostgresDependency(**interpolate_variables(raw_config["dependencies"]["postgres"]))


class Configuration(BaseSettings):
    model_config = ConfigDict(extra="allow")

    config_file: str = "config.yml"
    prometheus_multiproc_dir: str = "/tmp/prometheus_multiproc"

    @field_validator("config_file", mode="after")
    def config_file_exists(cls, config_file):
        if not Path(config_file).is_file():
            raise ValueError(f"Config file ({config_file}) not found.")
        return config_file

    @model_validator(mode="after")
    def setup_config(self) -> Any:
        config = ConfigurationFileSchema(**interpolate_variables(read_config_file(path=self.config_file)))

        self.models = config.models
        self.dependencies = config.dependencies
        self.settings = config.settings

        return self


@custom_validation_error
class ConfigurationFileSchema(HiddenInputSchema):
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
