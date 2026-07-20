from dataclasses import dataclass

from api.domain import SortField, SortOrder
from api.domain.key import KeyRepository
from api.domain.key.entities import KeyPage


@dataclass
class GetKeysCommand:
    user_id: int | None
    offset: int
    limit: int
    sort_by: SortField
    sort_order: SortOrder


@dataclass
class GetKeysUseCaseSuccess:
    key_page: KeyPage


type GetKeysUseCaseResult = GetKeysUseCaseSuccess


class GetKeysUseCase:
    def __init__(self, key_repository: KeyRepository):
        self.key_repository = key_repository

    async def execute(self, command: GetKeysCommand) -> GetKeysUseCaseResult:
        key_page = await self.key_repository.get_keys_page(
            user_id=command.user_id,
            limit=command.limit,
            offset=command.offset,
            sort_by=command.sort_by,
            sort_order=command.sort_order,
        )

        return GetKeysUseCaseSuccess(key_page=key_page)
