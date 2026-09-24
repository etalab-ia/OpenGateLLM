from datetime import UTC, datetime, timedelta
from http import HTTPMethod
import logging
from uuid import uuid4

from fastapi import BackgroundTasks
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.usage import UsageRepository
from api.domain.usage.entities import EnvironmentalImpacts, Usage, UsageBucket, UsageBucketPage
from api.infrastructure.fastapi.routes import EndpointRoute
from api.infrastructure.postgres._pagination import fetch_page_with_total
from api.infrastructure.postgres.models import Usage as UsageTable

logger = logging.getLogger(__name__)


class PostgresUsageRepository(UsageRepository):
    def __init__(self, postgres_session: AsyncSession, background_tasks: BackgroundTasks) -> None:
        self.postgres_session = postgres_session
        self.background_tasks = background_tasks
        self._row: UsageTable | None = None
        self._start_time: datetime | None = None

    def start_record(
        self,
        endpoint: EndpointRoute,
        model: str,
        user_id: int,
        router_id: int,
        router_name: str,
        user_email: str,
        key_id: int,
        key_name: str,
    ) -> str:
        self._start_time = datetime.now(tz=UTC)
        self._row = UsageTable(
            created=self._start_time,
            endpoint=f"/v1{endpoint}",
            method=HTTPMethod.POST,
            user_id=user_id,
            user_email=user_email,
            token_id=key_id,
            token_name=key_name,
            router_id=router_id,
            router_name=router_name,
        )
        return uuid4().hex

    def update_record(self, usage: Usage, provider_id: int, provider_model_name: str, first_token_at: datetime | None = None) -> None:
        if self._row is None or self._start_time is None:
            return

        now = datetime.now(tz=UTC)
        self._row.provider_id = provider_id
        self._row.provider_model_name = provider_model_name
        self._row.prompt_tokens = usage.prompt_tokens
        self._row.completion_tokens = usage.completion_tokens
        self._row.total_tokens = usage.total_tokens
        self._row.cost = usage.cost
        self._row.kwh = usage.impacts.kWh
        self._row.kgco2eq = usage.impacts.kgCO2eq
        self._row.status = 200
        self._row.latency = self._elapsed_ms(start_time=self._start_time, end_time=now)
        if first_token_at is not None:
            self._row.ttft = self._elapsed_ms(start_time=self._start_time, end_time=first_token_at)

    @staticmethod
    def _elapsed_ms(start_time: datetime, end_time: datetime) -> int:
        return round((end_time - start_time).total_seconds() * 1000)

    def fail_record(self, message: str, status: int) -> None:
        if self._row is None:
            return
        self._row.status = status

    def end_record(self) -> None:
        row = self._row
        self._row = None
        self._start_time = None
        if row is None:
            return
        self.background_tasks.add_task(self._persist, row)

    async def _persist(self, row: UsageTable) -> None:
        try:
            self.postgres_session.add(row)
            await self.postgres_session.commit()
        except Exception:
            logger.exception("Failed to persist usage row.")

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
