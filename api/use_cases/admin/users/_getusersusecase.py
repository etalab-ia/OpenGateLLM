from dataclasses import dataclass

from api.domain import SortOrder
from api.domain.user import UserRepository
from api.domain.user.entities import UserPage, UserSortField


@dataclass
class GetUsersCommand:
    role_id: int | None
    organization_id: int | None
    email: str | None = None
    offset: int = 0
    limit: int = 10
    sort_by: UserSortField = UserSortField.ID
    sort_order: SortOrder = SortOrder.ASC


@dataclass
class GetUsersUseCaseSuccess:
    user_page: UserPage


type GetUsersUseCaseResult = GetUsersUseCaseSuccess


class GetUsersUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def execute(self, command: GetUsersCommand) -> GetUsersUseCaseResult:
        user_page = await self.user_repository.get_users(
            role_id=command.role_id,
            organization_id=command.organization_id,
            email=command.email,
            offset=command.offset,
            limit=command.limit,
            sort_by=command.sort_by,
            sort_order=command.sort_order,
        )

        return GetUsersUseCaseSuccess(user_page=user_page)
