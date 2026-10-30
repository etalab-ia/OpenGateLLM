from dataclasses import dataclass

from api.domain import SortOrder
from api.domain.user import UserAuthorization, UserRepository
from api.domain.user.entities import UserPage, UserSortField
from api.domain.user.errors import UserCannotReadUsersError


@dataclass
class GetUsersCommand:
    authenticated_user_id: int
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


type GetUsersUseCaseResult = GetUsersUseCaseSuccess | UserCannotReadUsersError


class GetUsersUseCase:
    def __init__(self, user_repository: UserRepository, user_authorization: UserAuthorization):
        self.user_repository = user_repository
        self.user_authorization = user_authorization

    async def execute(self, command: GetUsersCommand) -> GetUsersUseCaseResult:
        is_authorized = await self.user_authorization.can_read_users(user_id=command.authenticated_user_id)

        if not is_authorized:
            return UserCannotReadUsersError(user_id=command.authenticated_user_id)

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
