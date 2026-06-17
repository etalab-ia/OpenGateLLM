from dataclasses import dataclass

from pydantic import FutureDatetime

from api.domain.key import KeyRepository
from api.domain.key.entities import Key
from api.domain.key.errors import KeyAlreadyExistsError
from api.domain.user.errors import UserNotFoundError


@dataclass
class CreateKeyCommand:
    user_id: int
    name: str
    expire: FutureDatetime | None


@dataclass
class CreateKeyUseCaseSuccess:
    key: Key


type CreateKeyUseCaseResult = CreateKeyUseCaseSuccess | KeyAlreadyExistsError | UserNotFoundError


class CreateKeyUseCase:
    def __init__(self, key_repository: KeyRepository):
        self.key_repository = key_repository

    async def execute(self, command: CreateKeyCommand) -> CreateKeyUseCaseResult:
        result = await self.key_repository.create_key(user_id=command.user_id, name=command.name, expire=command.expire)
        match result:
            case Key() as key:
                return CreateKeyUseCaseSuccess(key=key)
            case error:
                return error
