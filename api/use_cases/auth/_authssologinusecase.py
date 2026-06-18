from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from api.domain.auth import AuthSsoSessionValidator, SsoSessionClaims
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
    session_cookie: str
    name: str | None
    organization: str | None
    sub: str | None = None
    iss: str | None = None
    expires: int | None = None


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
        auth_sso_session_validator: AuthSsoSessionValidator,
        auth_login_type: Literal["password", "oidc"],
        auth_sso_default_role_id: int | None = None,
        auth_login_session_duration: int = 3600,
    ):
        self.key_repository = key_repository
        self.organization_repository = organization_repository
        self.user_repository = user_repository
        self.auth_sso_session_validator = auth_sso_session_validator

        self.auth_login_session_duration = auth_login_session_duration
        self.auth_login_type = auth_login_type
        self.auth_sso_default_role_id = auth_sso_default_role_id

    async def execute(self, command: AuthSsoLoginCommand) -> AuthSsoLoginUseCaseResult:
        if self.auth_login_type != "oidc":
            return InvalidOidcTokenError()

        result = await self.auth_sso_session_validator.validate_session(session_cookie=command.session_cookie)
        match result:
            case SsoSessionClaims() as session:
                pass
            case InvalidOidcTokenError() | SsoProviderNotAvailableError() as error:
                return error

        result = await self.user_repository.get_user_by_email(email=session.email)
        match result:
            case User() as user:
                pass
            case UserNotFoundError():
                if command.organization is not None:
                    result = await self.organization_repository.get_organization_by_name(name=command.organization)
                    match result:
                        case Organization() as organization:
                            organization_id = organization.id
                        case OrganizationNotFoundError():
                            organization = await self.organization_repository.create_organization(name=command.organization)
                            organization_id = organization.id
                else:
                    organization_id = None

                result = await self.user_repository.create_user(
                    role_id=self.auth_sso_default_role_id,
                    email=session.email,
                    name=command.name,
                    organization_id=organization_id,
                    sub=command.sub,
                    iss=command.iss,
                )
                match result:
                    case User() as user:
                        pass
                    case RoleNotFoundError() as error:
                        return error

        if command.expires:
            expires = datetime.fromtimestamp(command.expires, tz=UTC)
        else:
            expires = datetime.now(tz=UTC) + timedelta(seconds=self.auth_login_session_duration)
        key = await self.key_repository.upsert_key(user_id=user.id, name=self.REFRESH_KEY_NAME, expire=expires)

        return AuthSsoLoginUseCaseSuccess(key=key)
