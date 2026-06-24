import base64
from enum import StrEnum
from functools import wraps
import logging
import os
import re
from typing import Annotated, Any, Literal, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, constr, field_validator, model_validator
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
    url: constr(strip_whitespace=True, min_length=1) = Field(..., pattern=r"^redis://", description="Redis connection url.", examples=["redis://:changeme@localhost:6379"])  # fmt: off


@custom_validation_error()
class Dependencies(ConfigBaseModel):
    redis: RedisDependency | None = Field(default=None, description="Redis is a required dependency for the API to store rate limiting counters and performance metrics. It is an optional dependency for the Playground to use as stage manage (see [Reflex documentation](https://reflex.dev/docs/api-reference/config/)).")  # fmt: off


@custom_validation_error()
class Settings(ConfigBaseModel):
    auth_key_max_expiration_days: int | None = Field(default=None, ge=1, description="Maximum number of days for a new API key to be valid.")  # fmt: off
    routing_max_priority: int = Field(default=4, ge=0, description="Maximum allowed priority in routing tasks.")  # fmt: off
    app_title: str = Field(default=DEFAULT_APP_NAME, description="The title of the application (dsiplayed on Playground, Swagger and Redoc UI).")

    playground_opengatellm_url: str = Field(default="http://localhost:8000", description="The URL of the OpenGateLLM API.")
    playground_opengatellm_timeout: int = Field(default=60, description="The timeout in seconds for the OpenGateLLM API.")
    playground_disabled_pages: list[PlaygroundPages] = Field(default_factory=list, description="List of pages to disable from the navigation bar.")  # fmt: off
    playground_default_model: str | None = Field(default=None, description="The first model selected in chat page.")

    playground_theme_has_background: bool = Field(default=True, description="Whether the theme has a background.")
    playground_theme_accent_color: str = Field(default="purple", description="The primary color used for default buttons, typography, backgrounds, etc. See available colors at https://www.radix-ui.com/colors.")  # fmt: off
    playground_theme_appearance: str = Field(default="light", description="The appearance of the theme.")
    playground_theme_gray_color: str = Field(default="gray", description="The secondary color used for default buttons, typography, backgrounds, etc. See available colors at https://www.radix-ui.com/colors.")  # fmt: off
    playground_theme_panel_background: str = Field(default="solid", description="Whether panel backgrounds are translucent: 'solid' | 'translucent'.")
    playground_theme_radius: str = Field(default="medium", description="The radius of the theme. Can be 'small', 'medium', or 'large'.")
    playground_theme_scaling: str = Field(default="100%", description="The scaling of the theme.")
    playground_swagger_url: str | None = Field(default="http://localhost:8000/docs", pattern=r"^http[s]?://", description="Swagger URL. If not provided, deactivated swagger link in the navigation bar.")  # fmt: off
    playground_reference_url: str | None = Field(default="http://localhost:8000/redoc", pattern=r"^http[s]?://", description="Reference URL. If not provided, deactivated reference link in the navigation bar.")  # fmt: off
    playground_documentation_url: str | None = Field(default="https://docs.opengatellm.org", pattern=r"^http[s]?://", description="Documentation URL. If not provided, deactivated documentation link in the navigation bar.")  # fmt: off


class SettingsLoginPassword(Settings):
    auth_login_type: Literal["password"] = Field(default="password", description="Login type for the API.")


class SettingsLoginOIDC(Settings):
    auth_login_type: Literal["oidc"] = Field(default="oidc", description="Login type for the API.")

    auth_playground_url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = Field(default="http://localhost:8501", description="The URL of the application, use to whitelist domains in oauth2-proxy.")  # fmt: off
    auth_sso_oidc_issuer_url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = Field(description="OIDC issuer URL used to fetch JWKS and validate id_tokens.")  # fmt: off
    auth_sso_client_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = Field(description="OIDC client_id (audience) for id_token validation.")  # fmt: off
    auth_sso_client_secret: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = Field(description="OIDC client secret for id_token validation.")  # fmt: off
    auth_sso_cookie_secret: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1)] = Field(default=None, validate_default=True, description="Secret used to sign the OAuth2-proxy cookies. If not provided, a random secret will be generated. To generate a secret, you can see the dedicated section in the [OAuth2-proxy documentation](https://oauth2-proxy.github.io/oauth2-proxy/configuration/overview/#generating-a-cookie-secret).")  # fmt: off
    auth_sso_logout_redirect_uri: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = Field(description="The logout redirect uri for SSO.")  # fmt: off
    auth_sso_oidc_scope: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1)] = Field(default="openid", description="OIDC scope for id_token validation.")  # fmt: off
    auth_sso_cookie_secure: bool = Field(default=False, description="Whether the cookie is secure. Set to True if the application is served over HTTPS.")  # fmt: off
    auth_sso_name_claim_fields: list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]] = Field(default_factory=["name"], description="OIDC userinfo claim fields joined to build the user display name sent to the API on SSO login.")  # fmt: off
    auth_sso_groups_claim_field: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1)] = Field(default=None, description="OIDC groups claim name. Must be set if auth_sso_allowed_groups is set.")  # fmt: off
    auth_sso_allowed_groups: list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]] = Field(default_factory=list, description="OIDC groups allowed to access the application. When empty, all groups are allowed.")  # fmt: off
    auth_sso_allowed_email_domains: list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]] = Field(default_factory=list, description="OIDC whitelisted email domains. When empty, all email domains are allowed.")  # fmt: off
    auth_sso_organization_claim_field: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1)] = Field(default=None, description="OIDC organization claim name. When it set, organization will be automatically created if it doesn't exist. Must be set if auth_sso_allowed_organizations is set.")  # fmt: off
    auth_sso_allowed_organizations: list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]] = Field(default_factory=list, description="OIDC allowed organizations. When empty, all organizations are allowed.")  # fmt: off

    @field_validator("auth_sso_cookie_secret", mode="after")
    def set_auth_sso_cookie_secret(cls, value: str | None) -> str:
        if value is None:
            return base64.urlsafe_b64encode(os.urandom(32)).decode()
        return value

    @model_validator(mode="after")
    def validate_model(self) -> Any:
        if self.auth_sso_allowed_groups and not self.auth_sso_groups_claim_field:
            raise ValueError("If auth_sso_allowed_groups is set, auth_sso_groups_claim_field must be set.")

        if self.auth_sso_allowed_organizations and not self.auth_sso_organization_claim_field:
            raise ValueError("If auth_sso_allowed_organizations is set, auth_sso_organization_claim_field must be set.")
        return self


class ConfigFile(ConfigBaseModel):
    """
    The following parameters allow you to configure the Playground application. The configuration file can be shared with the API, as the sections are
    identical and compatible. Some parameters are common to both the API and the Playground (for example, `app_title`).

    For Plagroud deployment, some environment variables are required to be set, like Reflex backend URL. See
    [Environment variables](/configuration/environment_variable/#playground) for more information.
    """

    dependencies: Dependencies = Field(default_factory=Dependencies, description="Dependencies required by the applications (API and Playground).")  # fmt: off
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
