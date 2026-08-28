from dataclasses import dataclass

from api.domain.role import LimitRepository, PermissionRepository, RoleRepository
from api.domain.role.entities import Limit, PermissionType, Role
from api.domain.role.errors import RoleAlreadyExistsError, RoleNotFoundError


@dataclass
class UpdateRoleCommand:
    """Full replacement of the role persisted fields: empty lists clear permissions and limits."""

    role_id: int
    name: str
    permissions: list[PermissionType]
    limits: list[Limit]


@dataclass
class UpdateRoleUseCaseSuccess:
    role: Role


type UpdateRoleUseCaseResult = UpdateRoleUseCaseSuccess | RoleNotFoundError | RoleAlreadyExistsError


class UpdateRoleUseCase:
    def __init__(self, role_repository: RoleRepository, permission_repository: PermissionRepository, limit_repository: LimitRepository):
        self.role_repository = role_repository
        self.permission_repository = permission_repository
        self.limit_repository = limit_repository

    async def execute(self, command: UpdateRoleCommand) -> UpdateRoleUseCaseResult:
        role = await self.role_repository.get_role_with_permissions_and_limits_by_id(role_id=command.role_id)
        if isinstance(role, RoleNotFoundError):
            return role

        role_to_persist = role.with_name(command.name).with_limits(command.limits).with_permissions(command.permissions)

        await self.limit_repository.delete_limits_by_role_id(command.role_id)
        await self.limit_repository.create_limits(role_id=role.id, limits=command.limits)
        await self.permission_repository.delete_permissions_by_role_id(command.role_id)
        await self.permission_repository.create_permissions(role_id=role.id, permissions=command.permissions)

        if role_to_persist == role:
            return UpdateRoleUseCaseSuccess(role=role)

        update_result = await self.role_repository.update_role(role=role_to_persist)

        match update_result:
            case Role() as updated_role:
                return UpdateRoleUseCaseSuccess(role=updated_role)
            case error:
                return error
