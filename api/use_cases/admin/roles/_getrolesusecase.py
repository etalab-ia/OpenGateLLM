import asyncio
from dataclasses import dataclass, replace
import time

from api.domain import SortField, SortOrder
from api.domain.role import LimitRepository, PermissionRepository, RoleRepository
from api.domain.role.entities import RolePage
from api.domain.user import UserWithRoleQuery
from api.domain.user.errors import UserExpiredError, UserIsNotAdminError


@dataclass
class GetRolesCommand:
    user_id: int
    offset: int = 0
    limit: int = 10
    sort_by: SortField = SortField.ID
    sort_order: SortOrder = SortOrder.ASC


@dataclass
class GetRolesUseCaseSuccess:
    role_page: RolePage


type GetRolesUseCaseResult = GetRolesUseCaseSuccess | UserExpiredError | UserIsNotAdminError


class GetRolesUseCase:
    def __init__(
        self,
        role_repository: RoleRepository,
        permission_repository: PermissionRepository,
        limit_repository: LimitRepository,
        user_with_role_query: UserWithRoleQuery,
    ):
        self.role_repository = role_repository
        self.permission_repository = permission_repository
        self.limit_repository = limit_repository
        self.user_with_role_query = user_with_role_query

    async def execute(
        self,
        command: GetRolesCommand,
    ) -> GetRolesUseCaseResult:
        user = await self.user_with_role_query.get_user_with_role_by_id(user_id=command.user_id)

        if user.expires is not None and user.expires < time.time():
            return UserExpiredError()

        if not user.is_admin:
            return UserIsNotAdminError()

        role_page = await self.role_repository.get_roles_page(
            limit=command.limit, offset=command.offset, sort_by=command.sort_by, sort_order=command.sort_order
        )

        if role_page.data:
            role_ids = [role.id for role in role_page.data]
            limits, permissions = await asyncio.gather(
                self.limit_repository.get_limits_by_role_ids(role_ids=role_ids),
                self.permission_repository.get_permissions_by_role_ids(role_ids=role_ids),
            )

            full_roles = [role.with_limits(limits.get(role.id, [])).with_permissions(permissions.get(role.id, [])) for role in role_page.data]
            role_page = replace(role_page, data=full_roles)

        return GetRolesUseCaseSuccess(role_page=role_page)
