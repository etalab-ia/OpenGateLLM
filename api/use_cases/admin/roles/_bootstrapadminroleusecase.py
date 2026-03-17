from dataclasses import dataclass

from api.domain.role import RoleRepository
from api.domain.role.entities import Limit, PermissionType, Role
from api.domain.role.errors import RoleAlreadyExistsError


@dataclass
class BootstrapAdminRoleCommand:
    name: str
    permissions: list[PermissionType]
    limits: list[Limit]


@dataclass
class BootstrapAdminRoleUseCaseSuccess:
    role: Role


type BootstrapAdminRoleUseCaseResult = BootstrapAdminRoleUseCaseSuccess | RoleAlreadyExistsError


class BootstrapAdminRoleUseCase:
    def __init__(self, role_repository: RoleRepository):
        self.role_repository = role_repository

    async def execute(self, command: BootstrapAdminRoleCommand) -> BootstrapAdminRoleUseCaseResult:
        result = await self.role_repository.create_role(
            name=command.name,
            permissions=command.permissions,
            limits=command.limits,
        )

        match result:
            case Role() as role:
                return BootstrapAdminRoleUseCaseSuccess(role)
            case error:
                return error
