from dataclasses import dataclass

from api.domain.key import KeyRepository
from api.domain.key.entities import Key
from api.domain.key.errors import KeyNotFoundError


@dataclass
class DeleteKeyCommand:
    key_id: int
    user_id: int | None = None


@dataclass
class DeleteKeyUseCaseSuccess:
    key: Key


type DeleteKeyUseCaseResult = DeleteKeyUseCaseSuccess | KeyNotFoundError


class DeleteKeyUseCase:
    def __init__(self, key_repository: KeyRepository):
        self.key_repository = key_repository

    async def execute(self, command: DeleteKeyCommand) -> DeleteKeyUseCaseResult:
        result = await self.key_repository.delete_key(key_id=command.key_id, user_id=command.user_id)
        match result:
            case Key() as key:
                return DeleteKeyUseCaseSuccess(key=key)
            case error:
                return error
