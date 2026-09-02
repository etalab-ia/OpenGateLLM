from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.role import LimitRepository
from api.domain.role.entities import Limit
from api.sql.models import Limit as LimitTable


class PostgresLimitRepository(LimitRepository):
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    @staticmethod
    def _row_to_limit(row) -> Limit:
        return Limit(router_id=row.router_id, type=row.type, value=row.value)

    async def get_limits_by_role_ids(self, role_ids: list[int]) -> dict[int, list[Limit]]:
        limits_query = select(
            LimitTable.role_id,
            LimitTable.router_id,
            LimitTable.type,
            LimitTable.value,
        ).where(LimitTable.role_id.in_(role_ids))

        result = await self.postgres_session.execute(limits_query)
        limits: dict[int, list[Limit]] = {}
        for row in result.all():
            limits.setdefault(row.role_id, []).append(self._row_to_limit(row))
        return limits

    async def create_limits(self, role_id: int, limits: list[Limit]) -> list[Limit]:
        if not limits:
            return []

        result = await self.postgres_session.execute(
            insert(LimitTable)
            .values([{"role_id": role_id, "router_id": limit.router_id, "type": limit.type, "value": limit.value} for limit in limits])
            .on_conflict_do_nothing()
            .returning(LimitTable.router_id, LimitTable.type, LimitTable.value)
        )
        return [self._row_to_limit(row) for row in result.all()]

    async def delete_limits_by_role_id(self, role_id: int) -> list[Limit]:
        result = await self.postgres_session.execute(
            delete(table=LimitTable).where(LimitTable.role_id == role_id).returning(LimitTable.router_id, LimitTable.type, LimitTable.value)
        )
        return [self._row_to_limit(row) for row in result.all()]
