from dataclasses import dataclass

from api.domain.key import KeyRepository
from api.domain.key.entities import Key
from api.domain.key.errors import KeyNotFoundError


@dataclass
class GetOneKeyCommand:
    key_id: int


@dataclass
class GetOneKeyUseCaseSuccess:
    key: Key


type GetOneKeyUseCaseResult = GetOneKeyUseCaseSuccess | KeyNotFoundError


class GetOneKeyUseCase:
    def __init__(self, key_repository: KeyRepository):
        self.key_repository = key_repository

    async def execute(self, command: GetOneKeyCommand) -> GetOneKeyUseCaseResult:
        result = await self.key_repository.get_key_by_id(command.key_id)

        if isinstance(result, KeyNotFoundError):
            return result

        return GetOneKeyUseCaseSuccess(key=result)
