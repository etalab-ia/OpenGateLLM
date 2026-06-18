from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from api.domain.auth import AuthOidcProviderCache, AuthOidcProviderClient, AuthOidcTokenValidator
from api.domain.auth.errors import InvalidOidcTokenError, OidcProviderNotAvailableError
from api.domain.key import KeyRepository
from api.domain.key.entities import Key
from api.domain.role.errors import RoleNotFoundError
from api.domain.user import UserRepository
from api.domain.user.entities import User
from api.domain.user.errors import UserNotFoundError


@dataclass
class AuthOidcLoginCommand:
    email: str
    id_token: str


@dataclass
class AuthOidcLoginUseCaseSuccess:
    key: Key


type AuthOidcLoginUseCaseResult = AuthOidcLoginUseCaseSuccess | InvalidOidcTokenError | OidcProviderNotAvailableError | RoleNotFoundError


class AuthOidcLoginUseCase:
    REFRESH_KEY_NAME: str = "playground"

    def __init__(
        self,
        key_repository: KeyRepository,
        user_repository: UserRepository,
        auth_oidc_provider_client: AuthOidcProviderClient,
        auth_oidc_token_validator: AuthOidcTokenValidator,
        auth_oidc_provider_cache: AuthOidcProviderCache,
        oauth2_login_type: Literal["password", "oidc"],
        oauth2_oidc_issuer_url: str | None = None,
        oauth2_oidc_client_id: str | None = None,
        oauth2_default_role_id: int | None = None,
        login_session_duration: int = 3600,
    ):
        self.key_repository = key_repository
        self.user_repository = user_repository
        self.auth_oidc_provider_client = auth_oidc_provider_client
        self.auth_oidc_token_validator = auth_oidc_token_validator
        self.auth_oidc_provider_cache = auth_oidc_provider_cache

        self.login_session_duration = login_session_duration
        self.oauth2_login_type = oauth2_login_type
        self.oauth2_oidc_issuer_url = oauth2_oidc_issuer_url
        self.oauth2_oidc_client_id = oauth2_oidc_client_id
        self.oauth2_default_role_id = oauth2_default_role_id

    async def execute(self, command: AuthOidcLoginCommand) -> AuthOidcLoginUseCaseResult:
        if self.oauth2_login_type != "oidc":
            return InvalidOidcTokenError()

        jwks = await self.auth_oidc_provider_cache.get(email=self.oauth2_oidc_issuer_url)
        if jwks is None:
            result = await self.auth_oidc_provider_client.get_jwks(issuer_url=self.oauth2_oidc_issuer_url)
            match result:
                case dict() as jwks:
                    await self.auth_oidc_provider_cache.set(
                        email=self.oauth2_oidc_issuer_url,
                        claims=jwks,
                        expire=self.login_session_duration,
                    )
                case OidcProviderNotAvailableError() as error:
                    return error

        result = await self.auth_oidc_token_validator.validate_token(
            id_token=command.id_token,
            client_id=self.oauth2_oidc_client_id,
            jwks=jwks,
        )
        match result:
            case dict() as claims:
                pass
            case InvalidOidcTokenError() as error:
                if not error.stale_jwks:
                    return error

                # Retry validation with new JWKS
                await self.auth_oidc_provider_cache.delete(email=self.oauth2_oidc_issuer_url)
                result = await self.auth_oidc_provider_client.get_jwks(issuer_url=self.oauth2_oidc_issuer_url)
                match result:
                    case dict() as jwks:
                        await self.auth_oidc_provider_cache.set(email=self.oauth2_oidc_issuer_url, claims=jwks, expire=self.login_session_duration)
                    case OidcProviderNotAvailableError() as error:
                        return error

                result = await self.auth_oidc_token_validator.validate_token(
                    id_token=command.id_token,
                    client_id=self.oauth2_oidc_client_id,
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
                result = await self.user_repository.create_user(
                    role_id=self.oauth2_default_role_id,
                    email=command.email,
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
            expires = datetime.now(tz=UTC) + timedelta(seconds=self.login_session_duration)

        key = await self.key_repository.upsert_key(user_id=user.id, name=self.REFRESH_KEY_NAME, expire=expires)

        return AuthOidcLoginUseCaseSuccess(key=key)
