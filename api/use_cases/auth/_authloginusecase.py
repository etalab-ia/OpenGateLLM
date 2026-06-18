from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from api.domain.key import KeyRepository
from api.domain.key.entities import Key
from api.domain.user import UserRepository
from api.domain.user.entities import User
from api.domain.user.errors import InvalidUserPasswordError, UserNotFoundError


@dataclass
class AuthLoginCommand:
    email: str
    password: str


@dataclass
class AuthLoginUseCaseSuccess:
    key: Key


type AuthLoginUseCaseResult = AuthLoginUseCaseSuccess | UserNotFoundError | InvalidUserPasswordError


class AuthLoginUseCase:
    REFRESH_KEY_NAME: str = "playground"

    def __init__(self, key_repository: KeyRepository, user_repository: UserRepository, login_session_duration: int = 3600):
        self.key_repository = key_repository
        self.user_repository = user_repository
        self.login_session_duration = login_session_duration

    async def execute(self, command: AuthLoginCommand) -> AuthLoginUseCaseResult:
        result = await self.user_repository.get_user_password_by_email_and_password(email=command.email, password=command.password)
        match result:
            case User() as user:
                pass
            case error:
                return error

        expires = datetime.now(tz=UTC) + timedelta(seconds=self.login_session_duration)
        key = await self.key_repository.upsert_key(user_id=user.id, name=self.REFRESH_KEY_NAME, expire=expires)

        return AuthLoginUseCaseSuccess(key=key)
