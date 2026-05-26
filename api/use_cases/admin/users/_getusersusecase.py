from dataclasses import dataclass
import time

from api.domain import SortOrder
from api.domain.user import UserRepository, UserWithRoleQuery
from api.domain.user.entities import UserPage, UserSortField
from api.domain.user.errors import UserExpiredError, UserIsNotAdminError


@dataclass
class GetUsersCommand:
    authenticated_user_id: int
    role_id: int | None
    organization_id: int | None
    offset: int = 0
    limit: int = 10
    sort_by: UserSortField = UserSortField.ID
    sort_order: SortOrder = SortOrder.ASC


@dataclass
class GetUsersUseCaseSuccess:
    user_page: UserPage


type GetUsersCaseResult = GetUsersUseCaseSuccess | UserExpiredError | UserIsNotAdminError


class GetUsersUseCase:
    def __init__(self, user_repository: UserRepository, user_with_role_query: UserWithRoleQuery):
        self.user_repository = user_repository
        self.user_with_role_query = user_with_role_query

    async def execute(self, command: GetUsersCommand) -> GetUsersCaseResult:
        user = await self.user_with_role_query.get_user_with_role_by_id(user_id=command.authenticated_user_id)

        if user.expires is not None and user.expires < time.time():
            return UserExpiredError()

        if not user.is_admin:
            return UserIsNotAdminError()

        user_page = await self.user_repository.get_users(
            role_id=command.role_id,
            organization_id=command.organization_id,
            offset=command.offset,
            limit=command.limit,
            sort_by=command.sort_by,
            sort_order=command.sort_order,
        )

        return GetUsersUseCaseSuccess(user_page=user_page)
