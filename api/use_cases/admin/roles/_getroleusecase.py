from dataclasses import dataclass

from api.domain.role import LimitRepository, PermissionRepository, RoleRepository
from api.domain.role.entities import Role
from api.domain.role.errors import RoleNotFoundError
from api.domain.userinfo import UserInfoRepository
from api.domain.userinfo.errors import UserIsNotAdminError


@dataclass
class GetRoleCommand:
    user_id: int
    role_id: int


@dataclass
class GetRoleUseCaseSuccess:
    role: Role


type GetRoleUseCaseResult = GetRoleUseCaseSuccess | RoleNotFoundError | UserIsNotAdminError


class GetRoleUseCase:
    def __init__(
        self,
        role_repository: RoleRepository,
        permission_repository: PermissionRepository,
        limit_repository: LimitRepository,
        user_info_repository: UserInfoRepository,
    ):
        self.role_repository = role_repository
        self.permission_repository = permission_repository
        self.limit_repository = limit_repository
        self.user_info_repository = user_info_repository

    async def execute(
        self,
        command: GetRoleCommand,
    ) -> GetRoleUseCaseResult:
        user_info = await self.user_info_repository.get_user_info(user_id=command.user_id)

        if not user_info.is_admin:
            return UserIsNotAdminError()

        role = await self.role_repository.get_role_with_permissions_and_limits_by_id(role_id=command.role_id)
        if role is None:
            return RoleNotFoundError(role_id=command.role_id)
        return GetRoleUseCaseSuccess(role=role)
