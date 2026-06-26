from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Literal

from api.domain.auth import AuthSsoSessionValidator, SsoPolicyRepository
from api.domain.auth.errors import (
    DefaultSsoPolicyOrganizationIsNotSetError,
    DefaultSsoPolicyRoleIsNotSetError,
    SsoAccessDeniedError,
    SsoInvalidSessionError,
    SsoProviderNotAvailableError,
)
from api.domain.key import KeyRepository
from api.domain.key.entities import Key
from api.domain.role.errors import RoleNotFoundError
from api.domain.user import UserRepository
from api.domain.user.entities import User
from api.domain.user.errors import UserNotFoundError


@dataclass
class AuthSsoLoginCommand:
    session_cookie: str
    name: str | None
    organization: str | None
    roles: list[str] = field(default_factory=list)
    sub: str | None = None
    iss: str | None = None
    expires: int | None = None


@dataclass
class AuthSsoLoginUseCaseSuccess:
    key: Key


type AuthSsoLoginUseCaseResult = (
    AuthSsoLoginUseCaseSuccess
    | DefaultSsoPolicyOrganizationIsNotSetError
    | DefaultSsoPolicyRoleIsNotSetError
    | SsoInvalidSessionError
    | SsoProviderNotAvailableError
    | SsoAccessDeniedError
    | RoleNotFoundError
)


class AuthSsoLoginUseCase:
    REFRESH_KEY_NAME: str = "_playground_refreshed_key"

    def __init__(
        self,
        key_repository: KeyRepository,
        user_repository: UserRepository,
        sso_policy_repository: SsoPolicyRepository,
        auth_sso_session_validator: AuthSsoSessionValidator,
        auth_login_type: Literal["password", "oidc"],
        auth_login_session_duration: int = 3600,
    ):
        self.key_repository = key_repository
        self.user_repository = user_repository
        self.sso_policy_repository = sso_policy_repository
        self.auth_sso_session_validator = auth_sso_session_validator

        self.auth_login_session_duration = auth_login_session_duration
        self.auth_login_type = auth_login_type

    async def execute(self, command: AuthSsoLoginCommand) -> AuthSsoLoginUseCaseResult:
        if self.auth_login_type != "oidc":
            return SsoInvalidSessionError()

        result = await self.auth_sso_session_validator.validate_session(session_cookie=command.session_cookie)
        match result:
            case str() as email:
                pass
            case SsoInvalidSessionError() | SsoProviderNotAvailableError() as error:
                return error

        policy = await self.sso_policy_repository.get_policy()
        if not policy.is_allowed(email=email, organization=command.organization, roles=command.roles):
            return SsoAccessDeniedError()

        result = await self.user_repository.get_user_by_email(email=email)
        match result:
            case User() as user:
                pass
            case UserNotFoundError():
                organization_rule = policy.get_matching_organization_rule(organization=command.organization)
                role_rule = policy.get_matching_role_rule(roles=command.roles)

                if role_rule is None:
                    return DefaultSsoPolicyRoleIsNotSetError()

                if organization_rule is None:
                    return DefaultSsoPolicyOrganizationIsNotSetError()

                result = await self.user_repository.create_user(
                    role_id=role_rule.role_id,
                    email=email,
                    name=command.name,
                    organization_id=organization_rule.organization_id,
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
