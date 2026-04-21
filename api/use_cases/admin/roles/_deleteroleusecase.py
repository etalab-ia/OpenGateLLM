from dataclasses import dataclass

from api.domain.role import RoleRepository
from api.domain.role.entities import Role
from api.domain.role.errors import RoleHasUsersError, RoleNotFoundError
from api.domain.userinfo import UserInfoRepository
from api.domain.userinfo.errors import UserIsNotAdminError


@dataclass
class DeleteRoleCommand:
    user_id: int
    role_id: int


@dataclass
class DeleteRoleUseCaseSuccess:
    role: Role


type DeleteRoleUseCaseResult = DeleteRoleUseCaseSuccess | RoleNotFoundError | UserIsNotAdminError | RoleHasUsersError


class DeleteRoleUseCase:
    def __init__(
        self,
        role_repository: RoleRepository,
        user_info_repository: UserInfoRepository,
    ):
        self.role_repository = role_repository
        self.user_info_repository = user_info_repository

    async def execute(
        self,
        command: DeleteRoleCommand,
    ) -> DeleteRoleUseCaseResult:
        user_info = await self.user_info_repository.get_user_info(user_id=command.user_id)

        if not user_info.is_admin:
            return UserIsNotAdminError()
        role = await self.role_repository.get_role_with_permissions_and_limits_by_id(role_id=command.role_id)
        if role is None:
            return RoleNotFoundError(role_id=command.role_id)
        if role.users > 0:
            return RoleHasUsersError(role_id=command.role_id, number_of_users=role.users)
        await self.role_repository.delete_role(role_id=command.role_id)
        return DeleteRoleUseCaseSuccess(role=role)
