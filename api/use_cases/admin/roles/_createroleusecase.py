from dataclasses import dataclass

from api.domain.role import LimitRepository, PermissionRepository, RoleRepository
from api.domain.role.entities import Limit, PermissionType, Role
from api.domain.role.errors import RoleAlreadyExistsError


@dataclass
class CreateRoleCommand:
    name: str
    permissions: list[PermissionType]
    limits: list[Limit]


@dataclass
class CreateRoleUseCaseSuccess:
    role: Role


type CreateRoleUseCaseResult = CreateRoleUseCaseSuccess | RoleAlreadyExistsError


class CreateRoleUseCase:
    def __init__(
        self,
        role_repository: RoleRepository,
        permission_repository: PermissionRepository,
        limit_repository: LimitRepository,
    ):
        self.role_repository = role_repository
        self.permission_repository = permission_repository
        self.limit_repository = limit_repository

    async def execute(self, command: CreateRoleCommand) -> CreateRoleUseCaseResult:
        result = await self.role_repository.create_role(name=command.name)
        match result:
            case Role() as created_role:
                role = created_role
            case error:
                return error
        permissions = await self.permission_repository.create_permissions(role_id=role.id, permissions=command.permissions)
        limits = await self.limit_repository.create_limits(role_id=role.id, limits=command.limits)
        return CreateRoleUseCaseSuccess(role=role.model_copy(update={"permissions": permissions, "limits": limits}))
