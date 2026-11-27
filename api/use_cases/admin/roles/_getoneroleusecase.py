from dataclasses import dataclass

from api.domain.role import RoleAuthorization, RoleRepository
from api.domain.role.entities import Role
from api.domain.role.errors import RoleNotFoundError, UserCannotReadRoleError


@dataclass
class GetOneRoleCommand:
    authenticated_user_id: int
    role_id: int


@dataclass
class GetOneRoleUseCaseSuccess:
    role: Role


type GetOneRoleUseCaseResult = GetOneRoleUseCaseSuccess | RoleNotFoundError | UserCannotReadRoleError


class GetOneRoleUseCase:
    def __init__(self, role_repository: RoleRepository, role_authorization: RoleAuthorization):
        self.role_repository = role_repository
        self.role_authorization = role_authorization

    async def execute(self, command: GetOneRoleCommand) -> GetOneRoleUseCaseResult:
        is_authorized = await self.role_authorization.can_read_role(user_id=command.authenticated_user_id, role_id=command.role_id)
        if not is_authorized:
            return UserCannotReadRoleError(user_id=command.authenticated_user_id)

        result = await self.role_repository.get_role_with_permissions_and_limits_by_id(role_id=command.role_id)
        match result:
            case Role() as role:
                return GetOneRoleUseCaseSuccess(role=role)
            case RoleNotFoundError():
                return RoleNotFoundError(id=command.role_id)
