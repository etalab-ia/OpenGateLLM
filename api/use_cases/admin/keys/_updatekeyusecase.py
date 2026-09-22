from dataclasses import dataclass

from api.domain.key import KeyRepository
from api.domain.key.entities import Key
from api.domain.key.errors import KeyNotFoundError


@dataclass
class UpdateKeyCommand:
    key_id: int
    name: str
    user_id: int | None = None


@dataclass
class UpdateKeyUseCaseSuccess:
    key: Key


type UpdateKeyUseCaseResult = UpdateKeyUseCaseSuccess | KeyNotFoundError


class UpdateKeyUseCase:
    def __init__(self, key_repository: KeyRepository):
        self.key_repository = key_repository

    async def execute(self, command: UpdateKeyCommand) -> UpdateKeyUseCaseResult:
        result = await self.key_repository.get_key_by_id(command.key_id)
        match result:
            case KeyNotFoundError() as error:
                return error
            case Key() as key:
                pass

        if command.user_id is not None and key.user_id != command.user_id:
            return KeyNotFoundError(id=command.key_id)

        key_to_persist = key.with_name(command.name)
        if key_to_persist == key:
            return UpdateKeyUseCaseSuccess(key=key)

        update_result = await self.key_repository.update_key(key_to_persist)
        match update_result:
            case Key() as updated_key:
                return UpdateKeyUseCaseSuccess(key=updated_key)
            case error:
                return error
