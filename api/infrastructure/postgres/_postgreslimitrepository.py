from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.role import LimitRepository
from api.domain.role.entities import Limit
from api.sql.models import Limit as LimitTable


class PostgresLimitRepository(LimitRepository):
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    async def create_limits(self, role_id: int, limits: list[Limit]) -> list[Limit]:
        if not limits:
            return []

        result = await self.postgres_session.execute(
            insert(LimitTable)
            .values([{"role_id": role_id, "router_id": limit.router_id, "type": limit.type, "value": limit.value} for limit in limits])
            .on_conflict_do_nothing()
            .returning(LimitTable.router_id, LimitTable.type, LimitTable.value)
        )

        return [Limit(router_id=row.router_id, type=row.type, value=row.value) for row in result.all()]

    async def delete_limits_by_role_id(self, role_id: int) -> list[Limit]:
        result = await self.postgres_session.execute(
            delete(table=LimitTable).where(LimitTable.role_id == role_id).returning(LimitTable.router_id, LimitTable.type, LimitTable.value)
        )
        return [Limit(router_id=row.router_id, type=row.type, value=row.value) for row in result.all()]
