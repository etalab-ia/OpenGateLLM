from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.usage import UsageRepository
from api.domain.usage.entities import EnvironmentalImpacts, UsagePage, UsageRecord
from api.infrastructure.postgres._pagination import fetch_page_with_total
from api.sql.models import Usage as UsageTable


class PostgresUsageRepository(UsageRepository):
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    async def get_usages_page(
        self,
        user_id: int,
        start_time: datetime,
        end_time: datetime,
        offset: int,
        limit: int,
        endpoint: str | None = None,
    ) -> UsagePage:
        filters = [
            UsageTable.user_id == user_id,
            UsageTable.status >= 200,
            UsageTable.status < 300,
            UsageTable.created >= start_time,
            UsageTable.created <= end_time,
        ]
        if endpoint is not None:
            filters.append(UsageTable.endpoint == endpoint)

        usages_query = (
            select(UsageTable, func.count().over().label("total")).where(*filters).order_by(UsageTable.created.desc()).offset(offset).limit(limit)
        )
        count_query = select(func.count()).select_from(UsageTable).where(*filters)
        rows, total = await fetch_page_with_total(self.postgres_session, usages_query, count_query)

        usages = [self._to_usage_record(row[0]) for row in rows]

        return UsagePage(total=total, data=usages)

    @staticmethod
    def _to_usage_record(row: UsageTable) -> UsageRecord:
        return UsageRecord(
            model=row.router_name,
            key=row.token_name,
            endpoint=row.endpoint,
            prompt_tokens=row.prompt_tokens,
            completion_tokens=int(row.completion_tokens) if row.completion_tokens is not None else None,
            total_tokens=row.total_tokens,
            cost=row.cost,
            latency=row.latency,
            ttft=row.ttft,
            impacts=EnvironmentalImpacts(kWh=(row.kwh or 0.0), kgCO2eq=(row.kgco2eq or 0.0)),
            created=row.created,
        )
