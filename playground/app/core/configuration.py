from functools import wraps
import logging
import os
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, constr, field_validator, model_validator
from pydantic import ValidationError as PydanticValidationError
from pydantic_settings import BaseSettings
import yaml

from app.core.variables import DEFAULT_APP_NAME


def custom_validation_error(url: str | None = None):
    """
    Decorator to override Pydantic ValidationError to change error message.

    Args:
        url(Optional[str]): override Pydantic documentation URL by provided URL. If not provided, the error message will be the same as the original error message.
    """

    class ValidationError(Exception):
        def __init__(self, exc: PydanticValidationError, cls: BaseModel, url: str):
            super().__init__()
            error_count = exc.error_count()
            error_content = exc.errors()
            message = f"{error_count} validation error for {cls.__name__}\n"

            for error in error_content:
                url = url or error["url"]
                if error["type"] == "assertion_error":
                    message += f"{error["msg"]}\n"
                else:
                    if len(error["loc"]) > 0:
                        message += f"{error["loc"][0]}\n"
                    message += f"  {error["msg"]} [type={error["type"]}, input_value={error.get("input", "")}, input_type={type(error.get("input")).__name__}]\n"  # fmt: off
                    if len(error["loc"]) > 0:
                        description = cls.__pydantic_fields__[error["loc"][0]].description
                        if description:
                            message += f"\n  {description}\n"
                message += f"    For further information visit {url}\n\n"

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
                raise ValidationError(exc=e, cls=cls, url=url) from None  # hide previous traceback

        cls.__init__ = new_init
        return cls

    return decorator


class ConfigBaseModel(BaseModel):
    model_config = ConfigDict(extra="allow")


@custom_validation_error(url="https://docs.opengatellm.org/docs/getting-started/configuration_file#redisdependency-1")
class RedisDependency(ConfigBaseModel):
    url: constr(strip_whitespace=True, min_length=1) = Field(..., pattern=r"^redis://", description="Redis connection url.", examples=["redis://:changeme@localhost:6379"])  # fmt: off


@custom_validation_error(url="https://docs.opengatellm.org/docs/getting-started/configuration_file#dependencies-1")
class Dependencies(ConfigBaseModel):
    redis: RedisDependency | None = Field(default=None, description="Set the Redis connection url to use as stage manager. See https://reflex.dev/docs/api-reference/config/ for more information.")  # fmt: off


@custom_validation_error(url="https://docs.opengatellm.org/docs/getting-started/configuration_file#settings-1")
class Settings(ConfigBaseModel):
    auth_key_max_expiration_days: int | None = Field(default=None, ge=1, description="Maximum number of days for a token to be valid.")  # fmt: off
    routing_max_priority: int = Field(default=10, ge=0, description="Maximum allowed priority in routing tasks.")  # fmt: off
    app_title: str = Field(default=DEFAULT_APP_NAME, description="The title of the application.")

    playground_opengatellm_url: str = Field(default="http://localhost:8000", description="The URL of the OpenGateLLM API.")
    playground_opengatellm_timeout: int = Field(default=60, description="The timeout in seconds for the OpenGateLLM API.")
    playground_default_model: str | None = Field(default=None, description="The first model selected in chat page.")
    playground_theme_has_background: bool = Field(default=True, description="Whether the theme has a background.")
    playground_theme_accent_color: str = Field(default="purple", description="The primary color used for default buttons, typography, backgrounds, etc. See available colors at https://www.radix-ui.com/colors.")  # fmt: off
    playground_theme_appearance: str = Field(default="light", description="The appearance of the theme.")
    playground_theme_gray_color: str = Field(default="gray", description="The secondary color used for default buttons, typography, backgrounds, etc. See available colors at https://www.radix-ui.com/colors.")  # fmt: off
    playground_theme_panel_background: str = Field(default="solid", description="Whether panel backgrounds are translucent: 'solid' | 'translucent'.")
    playground_theme_radius: str = Field(default="medium", description="The radius of the theme. Can be 'small', 'medium', or 'large'.")
    playground_theme_scaling: str = Field(default="100%", description="The scaling of the theme.")

    swagger_url: str | None = Field(default="http://localhost:8000/docs", pattern=r"^http[s]?://", description="Swagger URL. If not provided, deactivated swagger link in the navigation bar.")  # fmt: off
    reference_url: str | None = Field(default="http://localhost:8000/redoc", pattern=r"^http[s]?://", description="Reference URL. If not provided, deactivated reference link in the navigation bar.")  # fmt: off
    documentation_url: str | None = Field(default="https://docs.opengatellm.org/docs", pattern=r"^http[s]?://", description="Documentation URL. If not provided, deactivated documentation link in the navigation bar.")  # fmt: off


class ConfigFile(ConfigBaseModel):
    """
    The following parameters allow you to configure the Playground application. The configuration file can be shared with the API, as the sections are
    identical and compatible. Some parameters are common to both the API and the Playground (for example, `app_title`).

    For Plagroud deployment, some environment variables are required to be set, like Reflex backend URL. See
    [Environment variables](../getting-started/environment_variables.md#playground) for more information.
    """

    dependencies: Dependencies = Field(default_factory=Dependencies, description="Dependencies used by the playground.")  # fmt: off
    settings: Settings = Field(default_factory=Settings, description="General settings configuration fields. Some fields are common to the API and the playground.")  # fmt: off


class Configuration(BaseSettings):
    model_config = ConfigDict(extra="allow")

    config_file: str = Field(default="../config.yml", description="Config file path.")

    @field_validator("config_file", mode="before")
    def config_file_exists(cls, config_file):
        assert os.path.exists(path=config_file), f"Config file ({config_file}) not found."
        return config_file

    @model_validator(mode="after")
    def setup_config(cls, values) -> Any:
        with open(file=values.config_file) as file:
            lines = file.readlines()

        uncommented_lines = [line for line in lines if not line.lstrip().startswith("#")]
        file_content = cls.replace_environment_variables(file_content="".join(uncommented_lines))
        config = ConfigFile(**yaml.safe_load(stream=file_content))

        values.dependencies = config.dependencies
        values.settings = config.settings

        return values

    @classmethod
    def replace_environment_variables(cls, file_content):
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

        file_content = env_variable_pattern.sub(replace_env_var, file_content)

        return file_content


configuration = Configuration()
