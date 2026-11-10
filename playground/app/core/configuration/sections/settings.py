import base64
from enum import StrEnum
import os
from typing import Annotated, Any, Literal

from pydantic import Field, StringConstraints, field_validator, model_validator

from app.core.configuration._interpolation import ConfigBaseModel
from app.core.configuration._validationerrors import custom_validation_error
from app.core.variables import DEFAULT_APP_NAME


class PlaygroundPages(StrEnum):
    ACCOUNT = "account"
    KEYS = "keys"
    ORGANIZATIONS = "organizations"
    PROVIDERS = "providers"
    ROLES = "roles"
    ROUTERS = "routers"
    USAGE = "usage"
    USERS = "users"


@custom_validation_error
class Settings(ConfigBaseModel):
    auth_key_max_expiration_days: Annotated[int | None, Field(default=None, ge=1, description="Maximum number of days for a new API key to be valid.")]  # fmt: off
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


class CompiledSettingsLoginOIDC(Settings):
    auth_login_type: Annotated[Literal["oidc"], Field(default="oidc", description="Login type for the API.")]  # fmt: off

    auth_sso_oidc_issuer_url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(description="OIDC issuer URL used to fetch JWKS and validate id_tokens.")]  # fmt: off
    auth_sso_logout_redirect_uri: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(description="The logout redirect uri for SSO.")]  # fmt: off


class SettingsLoginOIDC(CompiledSettingsLoginOIDC):
    auth_login_session_duration: Annotated[int, Field(default=3600, ge=1, description="Duration of login session for the playground in seconds. Also used as oauth2-proxy cookie expiration when SSO is enabled.")]  # fmt: off
    auth_playground_url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(default="http://localhost:8501", description="Playground URL. Used by oauth2-proxy for redirect whitelisting and by the API to validate SSO sessions via /oauth2/auth. Use an internal URL reachable from the API (for example http://playground:8501) for API configuration and a public URL reachable from the internet (for example https://playground.my-domain.com) for Playground configuration.")]  # fmt: off
    auth_sso_client_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(description="OIDC client_id (audience) for id_token validation.")]  # fmt: off
    auth_sso_client_secret: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(description="OIDC client secret for id_token validation.")]  # fmt: off
    auth_sso_cookie_secret: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1), Field(default=None, validate_default=True, description="Secret used to sign the OAuth2-proxy cookies. If not provided, a random secret will be generated. To generate a secret, you can see the dedicated section in the [OAuth2-proxy documentation](https://oauth2-proxy.github.io/oauth2-proxy/configuration/overview/#generating-a-cookie-secret).")]  # fmt: off
    auth_sso_oidc_scope: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1), Field(default="openid email", description="OIDC scope for id_token validation.")]  # fmt: off
    auth_sso_oidc_claims: Annotated[dict[str, Any] | None, Field(default=None, description="Optional OIDC claims parameter sent by oauth2-proxy to the authorization endpoint. Use it to request an authentication context, for example ProConnect multi-factor authentication via id_token.acr. When id_token.acr lists values, oauth2-proxy rejects (403) any id_token whose acr is not one of them. Omitted by default, so no extra factor is requested.")]  # fmt: off
    auth_sso_cookie_secure: bool = Field(default=False, description="Whether the cookie is secure. Set to True if the application is served over HTTPS.")  # fmt: off

    @field_validator("auth_sso_cookie_secret", mode="after")
    def set_auth_sso_cookie_secret(cls, value: str | None) -> str:
        if value is None:
            return base64.urlsafe_b64encode(os.urandom(32)).decode()
        return value
