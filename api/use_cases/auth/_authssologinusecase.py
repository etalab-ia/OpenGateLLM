from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from api.domain.auth import AuthSsoProviderCache, AuthSsoProviderClient, AuthSsoTokenValidator
from api.domain.auth.errors import InvalidOidcTokenError, SsoProviderNotAvailableError
from api.domain.key import KeyRepository
from api.domain.key.entities import Key
from api.domain.organization import OrganizationRepository
from api.domain.organization.entities import Organization
from api.domain.organization.errors import OrganizationNotFoundError
from api.domain.role.errors import RoleNotFoundError
from api.domain.user import UserRepository
from api.domain.user.entities import User
from api.domain.user.errors import UserNotFoundError


@dataclass
class AuthSsoLoginCommand:
    email: str
    name: str | None
    organization: str | None
    token: str


@dataclass
class AuthSsoLoginUseCaseSuccess:
    key: Key


type AuthSsoLoginUseCaseResult = AuthSsoLoginUseCaseSuccess | InvalidOidcTokenError | SsoProviderNotAvailableError | RoleNotFoundError


class AuthSsoLoginUseCase:
    REFRESH_KEY_NAME: str = "playground"

    def __init__(
        self,
        key_repository: KeyRepository,
        organization_repository: OrganizationRepository,
        user_repository: UserRepository,
        auth_sso_provider_client: AuthSsoProviderClient,
        auth_sso_token_validator: AuthSsoTokenValidator,
        auth_sso_provider_cache: AuthSsoProviderCache,
        auth_login_type: Literal["password", "oidc"],
        auth_sso_oidc_issuer_url: str | None = None,
        auth_sso_client_id: str | None = None,
        auth_sso_default_role_id: int | None = None,
        auth_login_session_duration: int = 3600,
    ):
        self.key_repository = key_repository
        self.organization_repository = organization_repository
        self.user_repository = user_repository
        self.auth_sso_provider_client = auth_sso_provider_client
        self.auth_sso_token_validator = auth_sso_token_validator
        self.auth_sso_provider_cache = auth_sso_provider_cache

        self.auth_login_session_duration = auth_login_session_duration
        self.auth_login_type = auth_login_type
        self.auth_sso_oidc_issuer_url = auth_sso_oidc_issuer_url
        self.auth_sso_client_id = auth_sso_client_id
        self.auth_sso_default_role_id = auth_sso_default_role_id

    async def execute(self, command: AuthSsoLoginCommand) -> AuthSsoLoginUseCaseResult:
        if self.auth_login_type != "oidc":
            return InvalidOidcTokenError()

        jwks = await self.auth_sso_provider_cache.get(email=self.auth_sso_oidc_issuer_url)
        if jwks is None:
            result = await self.auth_sso_provider_client.get_jwks(issuer_url=self.auth_sso_oidc_issuer_url)
            match result:
                case dict() as jwks:
                    await self.auth_sso_provider_cache.set(
                        email=self.auth_sso_oidc_issuer_url,
                        claims=jwks,
                        expire=self.auth_login_session_duration,
                    )
                case SsoProviderNotAvailableError() as error:
                    return error

        result = await self.auth_sso_token_validator.validate_token(
            token=command.token,
            client_id=self.auth_sso_client_id,
            jwks=jwks,
        )
        match result:
            case dict() as claims:
                pass
            case InvalidOidcTokenError() as error:
                if not error.stale_jwks:
                    return error

                # Retry validation with new JWKS
                await self.auth_sso_provider_cache.delete(email=self.auth_sso_oidc_issuer_url)
                result = await self.auth_sso_provider_client.get_jwks(issuer_url=self.auth_sso_oidc_issuer_url)
                match result:
                    case dict() as jwks:
                        await self.auth_sso_provider_cache.set(
                            email=self.auth_sso_oidc_issuer_url,
                            claims=jwks,
                            expire=self.auth_login_session_duration,
                        )
                    case SsoProviderNotAvailableError() as error:
                        return error

                result = await self.auth_sso_token_validator.validate_token(
                    token=command.token,
                    client_id=self.auth_sso_client_id,
                    jwks=jwks,
                )
                match result:
                    case dict() as claims:
                        pass
                    case InvalidOidcTokenError() as error:
                        return error

        result = await self.user_repository.get_user_by_email(email=command.email)
        match result:
            case User() as user:
                pass
            case UserNotFoundError():
                if command.organization is not None:
                    result = await self.organization_repository.get_organization_by_name(name=command.organization)
                    match result:
                        case Organization() as organization:
                            pass
                        case OrganizationNotFoundError() as error:
                            organization = await self.organization_repository.create_organization(name=command.organization)
                            organization_id = organization.id
                else:
                    organization_id = None

                result = await self.user_repository.create_user(
                    role_id=self.auth_sso_default_role_id,
                    email=command.email,
                    name=command.name,
                    organization_id=organization_id,
                    sub=claims.get("sub"),
                    iss=claims.get("iss"),
                )
                match result:
                    case User() as user:
                        pass
                    case RoleNotFoundError() as error:
                        return error

        if claims.get("exp"):
            expires = datetime.fromtimestamp(claims.get("exp"), tz=UTC)
        else:
            expires = datetime.now(tz=UTC) + timedelta(seconds=self.auth_login_session_duration)

        key = await self.key_repository.upsert_key(user_id=user.id, name=self.REFRESH_KEY_NAME, expire=expires)

        return AuthSsoLoginUseCaseSuccess(key=key)
