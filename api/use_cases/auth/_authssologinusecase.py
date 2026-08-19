from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from api.domain.auth import AuthSsoSessionValidator
from api.domain.auth.errors import SSOAccessDeniedError, SsoInvalidSessionError, SsoProviderNotAvailableError
from api.domain.key import KeyRepository
from api.domain.key.entities import Key
from api.domain.organization import OrganizationRepository
from api.domain.organization.errors import OrganizationNotFoundError
from api.domain.role import RoleRepository
from api.domain.role.errors import RoleNotFoundError
from api.domain.user import UserRepository
from api.domain.user.entities import User
from api.domain.user.errors import UserAlreadyExistsError, UserNotFoundError
from api.utils.variables import SYSTEM_PLAYGROUND_KEY_NAME


@dataclass
class AuthSsoLoginCommand:
    session_cookie: str
    sub: str
    iss: str
    exp: int
    claims: dict[str, Any]


@dataclass
class AuthSsoLoginUseCaseSuccess:
    key: Key


type AuthSsoLoginUseCaseResult = (
    AuthSsoLoginUseCaseSuccess
    | SsoInvalidSessionError
    | SsoProviderNotAvailableError
    | RoleNotFoundError
    | OrganizationNotFoundError
    | UserAlreadyExistsError
    | UserNotFoundError
    | SSOAccessDeniedError
)


class AuthSsoLoginUseCase:
    def __init__(
        self,
        key_repository: KeyRepository,
        organization_repository: OrganizationRepository,
        user_repository: UserRepository,
        role_repository: RoleRepository,
        auth_sso_session_validator: AuthSsoSessionValidator,
        auth_login_type: Literal["password", "oidc"],
        auth_sso_default_role_id: int,
        auth_sso_default_organization_id: int,
    ):
        self.key_repository = key_repository
        self.organization_repository = organization_repository
        self.user_repository = user_repository
        self.role_repository = role_repository
        self.auth_sso_session_validator = auth_sso_session_validator

        self.auth_login_type = auth_login_type
        self.auth_sso_default_role_id = auth_sso_default_role_id
        self.auth_sso_default_organization_id = auth_sso_default_organization_id

    async def has_access(self, claims: dict[str, Any]) -> bool:
        """
        Dummy function, override is file to implement your own access policy.
        See https://docs.opengatellm.org/features/users_management/sso#custom-access-policy for more information.
        """
        return True

    async def get_user_name(self, claims: dict[str, Any]) -> str | None:
        """
        Dummy function, override is file to implement your own user name resolution logic.
        See https://docs.opengatellm.org/features/users_management/sso#custom-user-name-resolution for more information.
        """
        return None

    async def get_role_id(self, claims: dict[str, Any]) -> int:
        """
        Dummy function, override is file to implement your own role resolution logic.
        See https://docs.opengatellm.org/features/users_management/sso#custom-role-resolution for more information.
        """
        return self.auth_sso_default_role_id

    async def get_organization_id(self, claims: dict[str, Any]) -> int:
        """
        Dummy function, override is file to implement your own organization resolution logic.
        See https://docs.opengatellm.org/features/users_management/sso#custom-organization-resolution for more information.
        """
        return self.auth_sso_default_organization_id

    async def execute(self, command: AuthSsoLoginCommand) -> AuthSsoLoginUseCaseResult:
        if self.auth_login_type != "oidc":
            return SsoInvalidSessionError()

        result = await self.auth_sso_session_validator.validate_session(session_cookie=command.session_cookie)
        match result:
            case str() as email:
                pass
            case error:
                return error

        try:
            if not await self.has_access(claims=command.claims):
                return SSOAccessDeniedError()

            user_name = await self.get_user_name(claims=command.claims)
            organization_id = await self.get_organization_id(claims=command.claims)
            role_id = await self.get_role_id(claims=command.claims)
        except Exception as e:
            return SsoProviderNotAvailableError()

        result = await self.user_repository.get_user_by_iss_and_sub(iss=command.iss, sub=command.sub)
        match result:
            case User() as user:
                pass
            case UserNotFoundError():
                result = await self.user_repository.get_user_by_email(email=email)
                match result:
                    case User() as user:  # override sub/iss if the user previously logged in with another method (password or another SSO)
                        pass
                    case UserNotFoundError():
                        result = await self.user_repository.create_user(
                            role_id=role_id,
                            email=email,
                            name=user_name,
                            organization_id=organization_id,
                            sub=command.sub,
                            iss=command.iss,
                            claims=command.claims,
                        )
                        match result:
                            case User() as user:
                                pass
                            case error:
                                return error

        if user.need_to_update(
            email=email,
            name=user_name,
            organization_id=organization_id,
            role_id=role_id,
            iss=command.iss,
            sub=command.sub,
            claims=command.claims,
        ):
            user = user.model_copy(
                update={
                    "email": email,
                    "name": user_name,
                    "organization_id": organization_id,
                    "role": role_id,
                    "iss": command.iss,
                    "sub": command.sub,
                    "claims": command.claims,
                }
            )
            result = await self.user_repository.update_user(user=user)
            match result:
                case User() as user:
                    pass
                case error:
                    return error

        expires = datetime.fromtimestamp(timestamp=command.exp, tz=UTC)
        key = await self.key_repository.upsert_key(user_id=user.id, name=SYSTEM_PLAYGROUND_KEY_NAME, expire=expires)

        return AuthSsoLoginUseCaseSuccess(key=key)
