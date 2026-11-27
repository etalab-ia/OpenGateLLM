from dataclasses import dataclass

from api.domain.role import RoleAuthorization, RoleRepository
from api.domain.role.entities import Role
from api.domain.role.errors import RoleHasUsersError, RoleNotFoundError, UserCannotDeleteRoleError


@dataclass
class DeleteRoleCommand:
    authenticated_user_id: int
    role_id: int


@dataclass
class DeleteRoleUseCaseSuccess:
    role: Role


type DeleteRoleUseCaseResult = DeleteRoleUseCaseSuccess | RoleHasUsersError | RoleNotFoundError | UserCannotDeleteRoleError


class DeleteRoleUseCase:
    def __init__(self, role_repository: RoleRepository, role_authorization: RoleAuthorization):
        self.role_repository = role_repository
        self.role_authorization = role_authorization

    async def execute(self, command: DeleteRoleCommand) -> DeleteRoleUseCaseResult:
        is_authorized = await self.role_authorization.can_delete_role(user_id=command.authenticated_user_id, role_id=command.role_id)
        if not is_authorized:
            return UserCannotDeleteRoleError(user_id=command.authenticated_user_id)

        result = await self.role_repository.delete_role(role_id=command.role_id)

        match result:
            case Role() as deleted_role:
                return DeleteRoleUseCaseSuccess(role=deleted_role)
            case RoleHasUsersError() as error:
                return error
            case RoleNotFoundError(id=role_id):
                return RoleNotFoundError(id=role_id)
