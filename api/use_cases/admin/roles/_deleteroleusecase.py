from dataclasses import dataclass
import time

from api.domain.role import RoleRepository
from api.domain.role.entities import Role
from api.domain.role.errors import RoleHasUsersError, RoleNotFoundError
from api.domain.user import UserWithRoleQuery
from api.domain.user.errors import UserExpiredError, UserIsNotAdminError


@dataclass
class DeleteRoleCommand:
    user_id: int
    role_id: int


@dataclass
class DeleteRoleUseCaseSuccess:
    role: Role


type DeleteRoleUseCaseResult = DeleteRoleUseCaseSuccess | RoleHasUsersError | RoleNotFoundError | UserExpiredError | UserIsNotAdminError


class DeleteRoleUseCase:
    def __init__(
        self,
        role_repository: RoleRepository,
        user_with_role_query: UserWithRoleQuery,
    ):
        self.role_repository = role_repository
        self.user_with_role_query = user_with_role_query

    async def execute(
        self,
        command: DeleteRoleCommand,
    ) -> DeleteRoleUseCaseResult:
        user = await self.user_with_role_query.get_user_with_role_by_id(user_id=command.user_id)

        if user.expires is not None and user.expires < time.time():
            return UserExpiredError()

        if not user.is_admin:
            return UserIsNotAdminError()

        result = await self.role_repository.get_role_with_permissions_and_limits_by_id(role_id=command.role_id)
        match result:
            case Role() as role:
                if role.users > 0:
                    return RoleHasUsersError(id=command.role_id, number_of_users=role.users)
            case RoleNotFoundError():
                return RoleNotFoundError(id=command.role_id)

        await self.role_repository.delete_role(role_id=command.role_id)
        return DeleteRoleUseCaseSuccess(role=result)
