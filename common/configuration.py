from functools import wraps
import logging
import os
from pathlib import Path
import re
from typing import Annotated, Any, Literal, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator
from pydantic import ValidationError as PydanticValidationError
from pydantic_settings import BaseSettings
import yaml

DEFAULT_APP_NAME = "OpenGateLLM"


def custom_validation_error(suffix: str = ""):
    """
    Decorator to override Pydantic ValidationError to change error message.

    Args:
        url(Optional[str]): override Pydantic documentation URL by provided URL. If not provided, the error message will be the same as the original error message.
    """

    class ValidationError(Exception):
        def __init__(
            self, exc: PydanticValidationError, cls: BaseModel, base_url: str = "https://docs.opengatellm.org/configuration/configuration_file"
        ):
            super().__init__()
            error_content = exc.errors()

            def resolve_model_for_error(model: type[BaseModel], loc: tuple[Any, ...]):
                current_model = model
                documentation_url = base_url

                for idx, part in enumerate(loc):
                    if not isinstance(part, str):
                        continue
                    if part not in current_model.__pydantic_fields__:
                        break

                    field_info = current_model.__pydantic_fields__[part]

                    annotation = field_info.annotation
                    next_model = None
                    origin = get_origin(annotation)
                    args = get_args(annotation)
                    candidates = args if origin is not None else (annotation,)

                    for candidate in candidates:
                        if isinstance(candidate, type) and issubclass(candidate, BaseModel):
                            next_model = candidate
                            break

                    if next_model is None:
                        break

                    current_model = next_model
                    documentation_url = f"{base_url}#{current_model.__name__.lower()}{suffix}"

                return documentation_url

            message = str(exc)
            for error in error_content:
                loc = tuple(error.get("loc", ()))
                documentation_url = resolve_model_for_error(cls, loc)
                original_line = f"    For further information visit {error['url']}"
                replacement_line = f"    For further information visit {documentation_url}"
                message = message.replace(original_line, replacement_line, 1)

            self.message = message

        def __str__(self):
            return self.message

    def decorator(cls: type[BaseModel]):
        original_init = cls.__init__

        @wraps(original_init)
        def new_init(self, **data):
            try:
                original_init(self, **data)
            except PydanticValidationError as e:
                raise ValidationError(exc=e, cls=cls) from None  # hide previous traceback

        cls.__init__ = new_init
        return cls

    return decorator


class ConfigBaseModel(BaseModel):
    model_config = ConfigDict(extra="allow")


def replace_environment_variables(file_content: str) -> str:
    env_variable_pattern = re.compile(r"\${([A-Z0-9_]+)(:-[^}]*)?}")

    def replace_env_var(match):
        env_variable_definition = match.group(0)
        env_variable_name = match.group(1)
        default_env_variable_value = match.group(2)[2:] if match.group(2) else None

        env_variable_value = os.getenv(env_variable_name)

        if env_variable_value is not None and env_variable_value != "":
            return env_variable_value
        elif default_env_variable_value is not None:
            return default_env_variable_value
        else:
            logging.warning(f"Environment variable {env_variable_name} not found or empty to replace {env_variable_definition}.")
            return env_variable_definition

    return env_variable_pattern.sub(replace_env_var, file_content)


def load_yaml_config(config_file: str) -> dict:
    with open(file=config_file) as file:
        lines = file.readlines()

    uncommented_lines = [line for line in lines if not line.lstrip().startswith("#")]
    file_content = replace_environment_variables(file_content="".join(uncommented_lines))
    return yaml.safe_load(stream=file_content)


@custom_validation_error()
class RedisDependency(ConfigBaseModel):
    """
    Redis is a required dependency of OpenGateLLM. Redis is used to store rate limiting counters and performance metrics.
    Pass all `from_url()` method arguments of `redis.asyncio.connection.ConnectionPool` class, see https://redis.readthedocs.io/en/stable/connections.html#redis.asyncio.connection.ConnectionPool.from_url for more information.
    """

    url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^redis://"), Field(..., description="Redis connection url.", examples=["redis://:changeme@localhost:6379"])]  # fmt: off


class Settings(ConfigBaseModel):
    """
    Settings fields shared by the API and the Playground.
    """

    app_title: str = Field(default=DEFAULT_APP_NAME, description="The title of the application (dsiplayed on Playground, Swagger and Redoc UI).", examples=["My API"])  # fmt: off
    routing_max_priority: int = Field(default=4, ge=0, le=10, description="Maximum allowed priority in routing tasks.")  # fmt: off
    auth_key_max_expiration_days: int | None = Field(default=None, ge=1, description="Maximum number of days for a new API key to be valid.")  # fmt: off
    auth_login_session_duration: int = Field(default=3600, ge=1, description="Duration of login session for the playground in seconds. Also used as oauth2-proxy cookie expiration when SSO is enabled.")  # fmt: off


class SettingsLoginPassword(Settings):
    auth_login_type: Literal["password"] = Field(default="password", description="Login type for the API.")  # fmt: off


class SettingsLoginOIDC(Settings):
    auth_login_type: Literal["oidc"] = Field(default="oidc", description="Login type for the API.")  # fmt: off
    auth_playground_url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = Field(description="Playground URL. Used by oauth2-proxy for redirect whitelisting and by the API to validate SSO sessions via /oauth2/auth. Use an internal URL reachable from the API (for example http://playground:8501) for API configuration and a public URL reachable from the internet (for example https://playground.my-domain.com) for Playground configuration.")  # fmt: off


class ConfigFile(ConfigBaseModel):
    @model_validator(mode="before")
    @classmethod
    def normalize(cls, data: Any) -> Any:
        if isinstance(data, dict) and isinstance(data.get("settings"), dict):
            settings = data["settings"]
            settings.setdefault("auth_login_type", "password")
        return data


class Configuration(BaseSettings):
    model_config = ConfigDict(extra="allow")

    config_file: str = "config.yml"

    @field_validator("config_file", mode="before")
    def config_file_exists(cls, config_file):
        assert Path(config_file).is_file(), f"Config file ({config_file}) not found."
        return config_file
