from dataclasses import dataclass
import time

from api.domain.user import UserRepository, UserWithRoleQuery
from api.domain.user.entities import User
from api.domain.user.errors import UserExpiredError, UserIsNotAdminError, UserNotFoundError


@dataclass
class GetOneUserCommand:
    user_id: int
    authenticated_user_id: int


@dataclass
class GetOneUserUseCaseSuccess:
    user: User


type GetOneUserCaseResult = GetOneUserUseCaseSuccess | UserNotFoundError | UserExpiredError | UserIsNotAdminError


class GetOneUserUseCase:
    def __init__(self, user_repository: UserRepository, user_with_role_query: UserWithRoleQuery):
        self.user_repository = user_repository
        self.user_with_role_query = user_with_role_query

    async def execute(self, command: GetOneUserCommand) -> GetOneUserCaseResult:
        user = await self.user_with_role_query.get_user_with_role_by_id(user_id=command.authenticated_user_id)

        if user.expires is not None and user.expires < time.time():
            return UserExpiredError()

        if not user.is_admin:
            return UserIsNotAdminError()

        result = await self.user_repository.get_user_by_id(user_id=command.user_id)

        match result:
            case User() as user:
                return GetOneUserUseCaseSuccess(user)
            case error:
                return error
