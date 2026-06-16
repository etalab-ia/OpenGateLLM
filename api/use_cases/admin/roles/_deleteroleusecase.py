from dataclasses import dataclass

from api.domain.role import RoleRepository
from api.domain.role.entities import Role
from api.domain.role.errors import RoleHasUsersError, RoleNotFoundError


@dataclass
class DeleteRoleCommand:
    role_id: int


@dataclass
class DeleteRoleUseCaseSuccess:
    role: Role


type DeleteRoleUseCaseResult = DeleteRoleUseCaseSuccess | RoleHasUsersError | RoleNotFoundError


class DeleteRoleUseCase:
    def __init__(self, role_repository: RoleRepository):
        self.role_repository = role_repository

    async def execute(self, command: DeleteRoleCommand) -> DeleteRoleUseCaseResult:
        result = await self.role_repository.get_role_with_permissions_and_limits_by_id(role_id=command.role_id)
        match result:
            case Role() as role:
                if role.users > 0:
                    return RoleHasUsersError(id=command.role_id, number_of_users=role.users)
            case RoleNotFoundError():
                return RoleNotFoundError(id=command.role_id)

        await self.role_repository.delete_role(role_id=command.role_id)
        return DeleteRoleUseCaseSuccess(role=result)
