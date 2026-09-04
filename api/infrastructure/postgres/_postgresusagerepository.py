from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.usage import UsageRepository
from api.domain.usage.entities import EnvironmentalImpacts, UsageBucket, UsageBucketPage
from api.infrastructure.postgres._pagination import fetch_page_with_total
from api.sql.models import Usage as UsageTable


class PostgresUsageRepository(UsageRepository):
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    @staticmethod
    def _utc_day_start():
        return func.timezone("UTC", func.date_trunc("day", func.timezone("UTC", UsageTable.created)))

    async def get_usage_buckets_page(
        self,
        user_id: int,
        start_time: datetime,
        end_time: datetime,
        offset: int,
        limit: int,
        endpoint: str | None = None,
        models: list[str] | None = None,
        key_id: int | None = None,
    ) -> UsageBucketPage:
        utc_day_start = self._utc_day_start()
        filters = [
            UsageTable.user_id == user_id,
            UsageTable.status >= 200,
            UsageTable.status < 300,
            UsageTable.created >= start_time,
            UsageTable.created <= end_time,
        ]
        if endpoint is not None:
            filters.append(UsageTable.endpoint == endpoint)
        if models:
            filters.append(UsageTable.router_name.in_(models))
        if key_id is not None:
            filters.append(UsageTable.token_id == key_id)

        buckets_query = (
            select(
                utc_day_start.label("start_time"),
                func.coalesce(func.sum(UsageTable.prompt_tokens), 0).label("prompt_tokens"),
                func.coalesce(func.sum(UsageTable.completion_tokens), 0).label("completion_tokens"),
                func.coalesce(func.sum(UsageTable.total_tokens), 0).label("total_tokens"),
                func.coalesce(func.sum(UsageTable.cost), 0.0).label("cost"),
                func.coalesce(func.sum(UsageTable.kwh), 0.0).label("kwh"),
                func.coalesce(func.sum(UsageTable.kgco2eq), 0.0).label("kgco2eq"),
                func.count().label("requests"),
                func.count().over().label("total"),
            )
            .where(*filters)
            .group_by(utc_day_start)
            .order_by(utc_day_start.desc())
            .offset(offset)
            .limit(limit)
        )
        count_query = select(func.count()).select_from(select(utc_day_start).where(*filters).group_by(utc_day_start).subquery())
        rows, total = await fetch_page_with_total(self.postgres_session, buckets_query, count_query)

        return UsageBucketPage(total=total, data=[self._row_to_usage_bucket(row) for row in rows])

    @staticmethod
    def _row_to_usage_bucket(row) -> UsageBucket:
        start_time = row.start_time
        return UsageBucket(
            start_time=start_time,
            end_time=start_time + timedelta(days=1),
            prompt_tokens=int(row.prompt_tokens or 0),
            completion_tokens=int(row.completion_tokens or 0),
            total_tokens=int(row.total_tokens or 0),
            cost=float(row.cost or 0.0),
            requests=int(row.requests or 0),
            impacts=EnvironmentalImpacts(kWh=float(row.kwh or 0.0), kgCO2eq=float(row.kgco2eq or 0.0)),
        )
