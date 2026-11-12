import os
from typing import Annotated, Any

from pydantic import ConfigDict, Field, field_validator, model_validator
from pydantic_settings import BaseSettings
import yaml

from ._interpolation import ConfigBaseModel
from ._validationerrors import custom_validation_error
from .sections import CompiledSettingsLoginOIDC, Dependencies, SettingsLoginOIDC, SettingsLoginPassword

DEFAULT_CONFIG_FILE = "../config.yml"


@custom_validation_error
class CompiledConfigFile(ConfigBaseModel):
    dependencies: Annotated[Dependencies, Field(default_factory=Dependencies, description="Dependencies required by the applications (API and Playground).")]  # fmt: off
    settings: Annotated[SettingsLoginPassword | CompiledSettingsLoginOIDC, Field(discriminator="auth_login_type", default_factory=SettingsLoginPassword, description="General settings configuration fields.")]  # fmt: off

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, data: Any) -> Any:
        if isinstance(data, dict) and isinstance(data.get("settings"), dict):
            settings = data["settings"]
            settings.setdefault("auth_login_type", "password")
        return data


class ConfigFile(CompiledConfigFile):
    """
    The following parameters allow you to configure the Playground application. The configuration file can be shared with the API, as the sections are
    identical and compatible. Some parameters are common to both the API and the Playground (for example, `app_title`).

    For Plagroud deployment, some environment variables are required to be set, like Reflex backend URL. See
    [Environment variables](/configuration/environment_variable/#playground) for more information.
    """

    settings: Annotated[SettingsLoginPassword | SettingsLoginOIDC, Field(discriminator="auth_login_type", default_factory=SettingsLoginPassword, description="General settings configuration fields.")]  # fmt: off


def read_config_file(path: str) -> dict:
    with open(file=path) as file:
        return yaml.safe_load(stream=file)


def get_settings_login_oidc() -> SettingsLoginOIDC:
    settings = read_config_file(path=os.getenv("CONFIG_FILE", DEFAULT_CONFIG_FILE)).get("settings") or {}
    return SettingsLoginOIDC(**settings)


class Configuration(BaseSettings):
    # Pydantic prints the rejected input in its errors, and this model is the one reporting those of the whole file.
    model_config = ConfigDict(extra="allow", hide_input_in_errors=True)

    config_file: str = Field(default=DEFAULT_CONFIG_FILE, description="Config file path.")

    @field_validator("config_file", mode="before")
    def config_file_exists(cls, config_file):
        assert os.path.exists(path=config_file), f"Config file ({config_file}) not found."
        return config_file

    @model_validator(mode="after")
    @classmethod
    def setup_config(cls, values) -> Any:
        config = CompiledConfigFile(**read_config_file(path=values.config_file))

        values.dependencies = config.dependencies
        values.settings = config.settings

        return values


configuration = Configuration()
