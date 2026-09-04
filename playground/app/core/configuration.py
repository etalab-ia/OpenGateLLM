import base64
from enum import StrEnum
from functools import wraps
import logging
import os
import re
from typing import Annotated, Any, Literal, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator
from pydantic import ValidationError as PydanticValidationError
from pydantic_settings import BaseSettings
import yaml

from app.core.variables import DEFAULT_APP_NAME


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


class PlaygroundPages(StrEnum):
    ACCOUNT = "account"
    KEYS = "keys"
    ORGANIZATIONS = "organizations"
    PROVIDERS = "providers"
    ROLES = "roles"
    ROUTERS = "routers"
    USAGE = "usage"
    USERS = "users"


class ConfigBaseModel(BaseModel):
    model_config = ConfigDict(extra="allow")


@custom_validation_error()
class RedisDependency(ConfigBaseModel):
    url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^redis://"), Field(..., description="Redis connection url.", examples=["redis://:changeme@localhost:6379"])]  # fmt: off


@custom_validation_error()
class Dependencies(ConfigBaseModel):
    redis: Annotated[RedisDependency | None, Field(default=None, description="Redis is a required dependency for the API to store rate limiting counters and performance metrics. It is an optional dependency for the Playground to use as stage manage (see [Reflex documentation](https://reflex.dev/docs/api-reference/config/)).")]  # fmt: off


@custom_validation_error()
class Settings(ConfigBaseModel):
    auth_key_max_expiration_days: Annotated[int | None, Field(default=None, ge=1, description="Maximum number of days for a new API key to be valid.")]  # fmt: off
    auth_login_session_duration: Annotated[int, Field(default=3600, ge=1, description="Duration of login session for the playground in seconds. Also used as oauth2-proxy cookie expiration when SSO is enabled.")]  # fmt: off
    routing_max_priority: Annotated[int, Field(default=4, ge=0, description="Maximum allowed priority in routing tasks.")]  # fmt: off
    app_title: Annotated[str, Field(default=DEFAULT_APP_NAME, description="The title of the application (dsiplayed on Playground, Swagger and Redoc UI).")]  # fmt: off

    playground_opengatellm_url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^http[s]?://"), Field(default="http://localhost:8000", description="The URL of the OpenGateLLM API.")]  # fmt: off
    playground_opengatellm_timeout: Annotated[int, Field(default=60, ge=1, description="The timeout in seconds for the OpenGateLLM API.")]  # fmt: off
    playground_disabled_pages: Annotated[list[PlaygroundPages], Field(default_factory=list, description="List of pages to disable from the navigation bar.")]  # fmt: off
    playground_default_model: Annotated[str | None, Field(default=None, description="The first model selected in chat page.")]  # fmt: off

    playground_theme_has_background: Annotated[bool, Field(default=True, description="Whether the theme has a background.")]  # fmt: off
    playground_theme_accent_color: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(default="purple", description="The primary color used for default buttons, typography, backgrounds, etc. See available colors at https://www.radix-ui.com/colors.")]  # fmt: off
    playground_theme_appearance: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(default="light", description="The appearance of the theme.")]  # fmt: off
    playground_theme_gray_color: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(default="gray", description="The secondary color used for default buttons, typography, backgrounds, etc. See available colors at https://www.radix-ui.com/colors.")]  # fmt: off
    playground_theme_panel_background: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(default="solid", description="Whether panel backgrounds are translucent: 'solid' | 'translucent'.")]  # fmt: off
    playground_theme_radius: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(default="medium", description="The radius of the theme. Can be 'small', 'medium', or 'large'.")]  # fmt: off
    playground_swagger_url: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^http[s]?://"), Field(default="http://localhost:8000/docs", description="Swagger URL. If not provided, deactivated swagger link in the navigation bar.")]  # fmt: off
    playground_reference_url: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^http[s]?://"), Field(default="http://localhost:8000/redoc", description="Reference URL. If not provided, deactivated reference link in the navigation bar.")]  # fmt: off
    playground_documentation_url: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^http[s]?://"), Field(default="https://docs.opengatellm.org", description="Documentation URL. If not provided, deactivated documentation link in the navigation bar.")]  # fmt: off
    playground_sso_access_denied_documentation_url: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^http[s]?://"), Field(default=None, description="URL displayed in the access denied page when SSO access is denied. If not provided, use the documentation URL.")]  # fmt: off

    @model_validator(mode="after")
    def validate_sso_access_denied_documentation_url(cls, value: str | None) -> str | None:
        if value is None:
            return cls.playground_documentation_url
        return value


class SettingsLoginPassword(Settings):
    auth_login_type: Annotated[Literal["password"], Field(default="password", description="Login type for the API.")]  # fmt: off


class SettingsLoginOIDC(Settings):
    auth_login_type: Annotated[Literal["oidc"], Field(default="oidc", description="Login type for the API.")]  # fmt: off

    auth_playground_url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(default="http://localhost:8501", description="Playground URL. Used by oauth2-proxy for redirect whitelisting and by the API to validate SSO sessions via /oauth2/auth. Use an internal URL reachable from the API (for example http://playground:8501) for API configuration and a public URL reachable from the internet (for example https://playground.my-domain.com) for Playground configuration.")]  # fmt: off
    auth_sso_oidc_issuer_url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(description="OIDC issuer URL used to fetch JWKS and validate id_tokens.")]  # fmt: off
    auth_sso_client_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(description="OIDC client_id (audience) for id_token validation.")]  # fmt: off
    auth_sso_client_secret: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(description="OIDC client secret for id_token validation.")]  # fmt: off
    auth_sso_cookie_secret: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1), Field(default=None, validate_default=True, description="Secret used to sign the OAuth2-proxy cookies. If not provided, a random secret will be generated. To generate a secret, you can see the dedicated section in the [OAuth2-proxy documentation](https://oauth2-proxy.github.io/oauth2-proxy/configuration/overview/#generating-a-cookie-secret).")]  # fmt: off
    auth_sso_logout_redirect_uri: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(description="The logout redirect uri for SSO.")]  # fmt: off
    auth_sso_oidc_scope: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1), Field(default="openid email", description="OIDC scope for id_token validation.")]  # fmt: off
    auth_sso_cookie_secure: bool = Field(default=False, description="Whether the cookie is secure. Set to True if the application is served over HTTPS.")  # fmt: off

    @field_validator("auth_sso_cookie_secret", mode="after")
    def set_auth_sso_cookie_secret(cls, value: str | None) -> str:
        if value is None:
            return base64.urlsafe_b64encode(os.urandom(32)).decode()
        return value


class ConfigFile(ConfigBaseModel):
    """
    The following parameters allow you to configure the Playground application. The configuration file can be shared with the API, as the sections are
    identical and compatible. Some parameters are common to both the API and the Playground (for example, `app_title`).

    For Plagroud deployment, some environment variables are required to be set, like Reflex backend URL. See
    [Environment variables](/configuration/environment_variable/#playground) for more information.
    """

    dependencies: Annotated[Dependencies, Field(default_factory=Dependencies, description="Dependencies required by the applications (API and Playground).")]  # fmt: off
    settings: Annotated[SettingsLoginPassword | SettingsLoginOIDC, Field(discriminator="auth_login_type", default_factory=SettingsLoginPassword, description="General settings configuration fields.")]  # fmt: off

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, data: Any) -> Any:
        if isinstance(data, dict) and isinstance(data.get("settings"), dict):
            settings = data["settings"]
            settings.setdefault("auth_login_type", "password")
        return data


class Configuration(BaseSettings):
    model_config = ConfigDict(extra="allow")

    config_file: str = Field(default="../config.yml", description="Config file path.")

    @field_validator("config_file", mode="before")
    def config_file_exists(cls, config_file):
        assert os.path.exists(path=config_file), f"Config file ({config_file}) not found."
        return config_file

    @model_validator(mode="after")
    @classmethod
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
