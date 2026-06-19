from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from api.domain.key import KeyRepository
from api.domain.key.entities import Key
from api.domain.user import UserPasswordEncoder, UserRepository
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

    def __init__(
        self,
        key_repository: KeyRepository,
        user_repository: UserRepository,
        user_password_encoder: UserPasswordEncoder,
        login_session_duration: int = 3600,
    ):
        self.key_repository = key_repository
        self.user_repository = user_repository
        self.user_password_encoder = user_password_encoder
        self.login_session_duration = login_session_duration

    async def execute(self, command: AuthLoginCommand) -> AuthLoginUseCaseResult:
        result = await self.user_repository.get_user_id_and_password_by_email(email=command.email)
        match result:
            case UserNotFoundError() as error:
                return error
            case _:
                user_id, encoded_password = result
                if encoded_password is None:
                    return InvalidUserPasswordError()
                if not self.user_password_encoder.validate_password(password=command.password, encoded_password=encoded_password):
                    return InvalidUserPasswordError()

        expires = datetime.now(tz=UTC) + timedelta(seconds=self.login_session_duration)
        key = await self.key_repository.upsert_key(user_id=user_id, name=self.REFRESH_KEY_NAME, expire=expires)

        return AuthLoginUseCaseSuccess(key=key)
