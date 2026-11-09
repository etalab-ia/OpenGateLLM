from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AfterValidator, Field, StringConstraints, field_validator

from api.infrastructure.configuration._validationerrors import HiddenInputSchema, custom_validation_error
from api.infrastructure.fastapi.routes import RouterName
from api.infrastructure.fastapi.schemas import reject_password_over_max_bytes

DEFAULT_APP_NAME: str = "OpenGateLLM"


class LimitingStrategy(StrEnum):
    MOVING_WINDOW = "moving_window"
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"


class Tokenizer(StrEnum):
    TIKTOKEN_GPT2 = "tiktoken_gpt2"
    TIKTOKEN_R50K_BASE = "tiktoken_r50k_base"
    TIKTOKEN_P50K_BASE = "tiktoken_p50k_base"
    TIKTOKEN_P50K_EDIT = "tiktoken_p50k_edit"
    TIKTOKEN_CL100K_BASE = "tiktoken_cl100k_base"
    TIKTOKEN_O200K_BASE = "tiktoken_o200k_base"


@custom_validation_error
class Settings(HiddenInputSchema):
    """
    General settings configuration fields.
    """

    # general
    disabled_routers: Annotated[list[RouterName], Field(default_factory=list, description="Disabled routers to limits services of the API.", examples=[["embeddings"]], json_schema_extra={"default": []})]  # fmt: off
    hidden_routers: Annotated[list[RouterName], Field(default_factory=list, description="Routers are enabled but hidden in the swagger and the documentation of the API.", examples=[["admin"]], json_schema_extra={"default": []})]  # fmt: off
    app_title: Annotated[str, Field(default=DEFAULT_APP_NAME, description="The title of the application (dsiplayed on Playground, Swagger and Redoc UI).", examples=["My API"])]  # fmt: off

    # usage tokenizer
    usage_tokenizer: Annotated[Tokenizer, Field(default=Tokenizer.TIKTOKEN_GPT2, description="Tokenizer used to compute usage of the API.")]  # fmt: off

    # logging
    log_level: Annotated[Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], Field(default="INFO", description="Logging level of the API.")]  # fmt: off
    log_config: Annotated[str | None, Field(default=None, description="Path to a logging configuration file (YAML or JSON, Python dictConfig schema) applied to the API process. Logs are JSON by default; set this file to render them otherwise, or to route them elsewhere. When set, log_level no longer applies. See logging.example.yml.", examples=["logging.yml"])]  # fmt: off

    # swagger
    swagger_summary: Annotated[str, Field(default="OpenGateLLM connect to your models. You can configure this swagger UI in the configuration file, like hide routes or change the title.", description="Display summary of your API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.", examples=["My API description."])]  # fmt: off
    swagger_version: Annotated[str, Field(default="latest", description="Display version of your API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.", examples=["2.5.0"])]  # fmt: off
    swagger_description: Annotated[str, Field(default="[See documentation](https://github.com/etalab-ia/opengatellm/blob/main/README.md)", description="Display description of your API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.", examples=["[See documentation](https://github.com/etalab-ia/opengatellm/blob/main/README.md)"])]  # fmt: off
    swagger_contact: Annotated[dict | None, Field(default=None, description="Contact informations of the API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.")]  # fmt: off
    swagger_license_info: Annotated[dict, Field(default={"name": "MIT Licence", "identifier": "MIT", "url": "https://raw.githubusercontent.com/etalab-ia/opengatellm/refs/heads/main/LICENSE"}, description="Licence informations of the API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.")]  # fmt: off
    swagger_terms_of_service: Annotated[str | None, Field(default=None, description="A URL to the Terms of Service for the API in swagger UI. If provided, this has to be a URL.", examples=["https://example.com/terms-of-service"])]  # fmt: off
    swagger_openapi_tags: Annotated[list[dict[str, str | dict[str, str]]], Field(default_factory=list, description="OpenAPI tags of the API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.", json_schema_extra={"default": []})]  # fmt: off
    swagger_openapi_url: Annotated[str, Field(default="/openapi.json", pattern=r"^/", description="OpenAPI URL of swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.")]  # fmt: off
    swagger_docs_url: Annotated[str, Field(default="/docs", pattern=r"^/", description="Docs URL of swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.")]  # fmt: off
    swagger_redoc_url: Annotated[str, Field(default="/redoc", pattern=r"^/", description="Redoc URL of swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.")]  # fmt: off

    # auth
    auth_secret_key: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(description="Secret key for the API. It should be a random string with at least 32 characters. This key is used to encrypt user tokens, watch out if you modify the secret key, you'll need to update all user API keys.")]  # fmt: off
    auth_bootsrap_admin_username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=254), Field(default="admin", description="Username of the admin user created at the first startup.")]  # fmt: off
    auth_bootsrap_admin_password: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), AfterValidator(reject_password_over_max_bytes), Field(default="changeme", description="Password of the admin user created at the first startup. At most 72 bytes once UTF-8 encoded.")]  # fmt: off
    auth_key_max_expiration_days: Annotated[int | None, Field(default=None, ge=1, description="Maximum number of days for a new API key to be valid.")]  # fmt: off
    auth_login_session_duration: Annotated[int, Field(default=3600, ge=1, description="Duration of login session for the playground in seconds. Also used as oauth2-proxy cookie expiration when SSO is enabled.")]  # fmt: off

    # rate_limiting
    rate_limiting_strategy: Annotated[LimitingStrategy, Field(default=LimitingStrategy.FIXED_WINDOW, description="Rate limiting strategy for the API.")]  # fmt: off
    rate_limiting_cached_tokens_discount: Annotated[float, Field(default=0.8, ge=0.0, le=1.0, description="Share of cached prompt tokens deducted from TPM and TPD limits.")]  # fmt: off

    # monitoring
    monitoring_prometheus_enabled: Annotated[bool, Field(default=True, description="If true, Prometheus metrics will be exposed in the `/metrics` endpoint.")]  # fmt: off

    # audio
    audio_file_size_limit: Annotated[int | None, Field(default=None, ge=0, description="Maximum size of the audio file in bytes. If not provided, the audio file size limit is not applied.", examples=[100_000_000])]  # fmt: off

    @field_validator("log_config", mode="after")
    def log_config_exists(cls, log_config):
        if log_config is not None and not Path(log_config).is_file():
            raise ValueError(f"Logging configuration file ({log_config}) not found.")
        return log_config


class SettingsLoginPassword(Settings):
    auth_login_type: Annotated[Literal["password"], Field(default="password", description="Login type for the API.")]  # fmt: off


class SettingsLoginOIDC(Settings):
    auth_login_type: Annotated[Literal["oidc"], Field(default="oidc", description="Login type for the API.")]  # fmt: off
    auth_playground_url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(description="Playground URL. Used by oauth2-proxy for redirect whitelisting and by the API to validate SSO sessions via /oauth2/auth. Use an internal URL reachable from the API (for example http://playground:8501) for API configuration and a public URL reachable from the internet (for example https://playground.my-domain.com) for Playground configuration.")]  # fmt: off
    auth_sso_default_role_id: Annotated[int, Field(ge=1, description="Default role ID for SSO users.")]  # fmt: off
    auth_sso_default_organization_id: Annotated[int, Field(ge=1, description="Default organization ID for SSO users.")]  # fmt: off
