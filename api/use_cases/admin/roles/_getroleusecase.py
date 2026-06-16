from dataclasses import dataclass

from api.domain.role import RoleRepository
from api.domain.role.entities import Role
from api.domain.role.errors import RoleNotFoundError


@dataclass
class GetRoleCommand:
    role_id: int


@dataclass
class GetRoleUseCaseSuccess:
    role: Role


type GetRoleUseCaseResult = GetRoleUseCaseSuccess | RoleNotFoundError


class GetRoleUseCase:
    def __init__(self, role_repository: RoleRepository):
        self.role_repository = role_repository

    async def execute(self, command: GetRoleCommand) -> GetRoleUseCaseResult:
        result = await self.role_repository.get_role_with_permissions_and_limits_by_id(role_id=command.role_id)
        match result:
            case Role() as role:
                return GetRoleUseCaseSuccess(role=role)
            case RoleNotFoundError():
                return RoleNotFoundError(id=command.role_id)
