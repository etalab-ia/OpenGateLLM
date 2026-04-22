from dataclasses import dataclass

from api.domain.role import LimitRepository, PermissionRepository, RoleRepository
from api.domain.role.entities import Limit, PermissionType, Role
from api.domain.role.errors import RoleAlreadyExistsError, RoleNotFoundError
from api.domain.userinfo import UserInfoRepository
from api.domain.userinfo.errors import UserIsNotAdminError


@dataclass
class UpdateRoleCommand:
    user_id: int
    role_id: int
    name: str | None
    permissions: list[PermissionType] | None
    limits: list[Limit] | None


@dataclass
class UpdateRoleUseCaseSuccess:
    role: Role


type UpdateRoleUseCaseResult = UpdateRoleUseCaseSuccess | RoleNotFoundError | RoleAlreadyExistsError | UserIsNotAdminError


class UpdateRoleUseCase:
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

    async def execute(self, command: UpdateRoleCommand) -> UpdateRoleUseCaseResult:
        user_info = await self.user_info_repository.get_user_info(user_id=command.user_id)

        if not user_info.is_admin:
            return UserIsNotAdminError()

        role = await self.role_repository.get_role_with_permissions_and_limits_by_id(role_id=command.role_id)
        if isinstance(role, RoleNotFoundError):
            return role
        role_to_persist = role
        if command.name is not None:
            role_to_persist = role_to_persist.with_name(command.name)
        if command.limits is not None:
            role_to_persist = role_to_persist.with_limits(command.limits)
            await self.limit_repository.delete_limits_by_role_id(command.role_id)
            await self.limit_repository.create_limits(role_id=role.id, limits=command.limits)
        if command.permissions is not None:
            role_to_persist = role_to_persist.with_permissions(command.permissions)
            await self.permission_repository.delete_permissions_by_role_id(command.role_id)
            await self.permission_repository.create_permissions(role_id=role.id, permissions=command.permissions)
        if role_to_persist == role:
            return UpdateRoleUseCaseSuccess(role=role)

        update_result = await self.role_repository.update_role(role_to_persist)

        match update_result:
            case Role() as updated_role:
                return UpdateRoleUseCaseSuccess(role=updated_role)
            case error:
                return error
