from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from pydantic import FutureDatetime

from api.domain.key import KeyRepository
from api.domain.key.entities import Key
from api.domain.key.errors import KeyAlreadyExistsError, KeyExpirationInvalidError
from api.domain.user.errors import UserNotFoundError


@dataclass
class CreateKeyCommand:
    user_id: int
    name: str
    expire: FutureDatetime | None


@dataclass
class CreateKeyUseCaseSuccess:
    key: Key


type CreateKeyUseCaseResult = KeyAlreadyExistsError | CreateKeyUseCaseSuccess | KeyExpirationInvalidError | UserNotFoundError


class CreateKeyUseCase:
    def __init__(self, key_repository: KeyRepository, key_max_expiration_days: int | None = None):
        self.key_repository = key_repository
        self.key_max_expiration_days = key_max_expiration_days

    async def execute(self, command: CreateKeyCommand) -> CreateKeyUseCaseResult:
        expire = command.expire
        if self.key_max_expiration_days:
            max_expires = datetime.now(tz=UTC) + timedelta(days=self.key_max_expiration_days)
            if expire is None:
                expire = max_expires
            elif expire > max_expires:
                return KeyExpirationInvalidError(max_expiration_days=self.key_max_expiration_days)

        result = await self.key_repository.create_key(user_id=command.user_id, name=command.name, expire=expire)
        match result:
            case Key() as key:
                return CreateKeyUseCaseSuccess(key=key)
            case error:
                return error
