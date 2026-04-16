from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.role import PermissionRepository
from api.domain.role.entities import PermissionType
from api.sql.models import Permission as PermissionTable


class PostgresPermissionRepository(PermissionRepository):
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    async def get_permissions_by_role_ids(self, role_ids: list[int]) -> dict[int, list[PermissionType]]:
        permissions_query = select(PermissionTable.role_id, PermissionTable.permission).where(PermissionTable.role_id.in_(role_ids))

        result = await self.postgres_session.execute(permissions_query)
        permissions: dict[int, list[PermissionType]] = {}
        for row in result.all():
            permissions.setdefault(row.role_id, []).append(PermissionType(row.permission))
        return permissions

    async def create_permissions(self, role_id: int, permissions: list[PermissionType]) -> list[PermissionType]:
        if not permissions:
            return []

        result = await self.postgres_session.execute(
            insert(PermissionTable)
            .values([{"role_id": role_id, "permission": permission} for permission in permissions])
            .on_conflict_do_nothing()
            .returning(PermissionTable.permission)
        )

        return [PermissionType(row.permission) for row in result.all()]

    async def delete_permissions_by_role_id(self, role_id: int) -> list[PermissionType]:
        result = await self.postgres_session.execute(
            delete(table=PermissionTable).where(PermissionTable.role_id == role_id).returning(PermissionTable.permission)
        )
        return [PermissionType(row.permission) for row in result.all()]
