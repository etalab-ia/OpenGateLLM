import datetime as dt
import time

from sqlalchemy import Integer, cast, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from api.schemas.me.usage import (
    CarbonFootprintUsage,
    EndpointUsage,
    MetricsUsage,
    Usage,
    UsageDetail,
)
from api.sql.models import Usage as UsageTable


class UsageManager:
    """Manager class for handling usage-related database operations and data processing."""

    async def get_usages(
        self,
        postgres_session: AsyncSession,
        user_id: int,
        offset: int,
        limit: int,
        start_time: int | None = None,
        end_time: int | None = None,
        endpoint: EndpointUsage | None = None,
    ) -> list[Usage]:
        if start_time is None:
            start_time = int(time.time() - 30 * 24 * 60 * 60)
        if end_time is None:
            end_time = int(time.time())

        query = (
            select(
                UsageTable.router_name.label("model"),
                UsageTable.token_name.label("key"),
                UsageTable.endpoint,
                UsageTable.prompt_tokens,
                UsageTable.completion_tokens,
                UsageTable.total_tokens,
                UsageTable.cost,
                UsageTable.latency,
                UsageTable.ttft,
                UsageTable.kwh,
                UsageTable.kgco2eq,
                cast(func.extract("epoch", UsageTable.created), Integer).label("created"),
            )
            .where(
                UsageTable.user_id == user_id,
                UsageTable.status >= 200,
                UsageTable.status < 300,
                UsageTable.created >= dt.datetime.fromtimestamp(start_time),
                UsageTable.created <= dt.datetime.fromtimestamp(end_time),
            )
            .order_by(UsageTable.created.desc())
            .offset(offset)
            .limit(limit)
        )

        if endpoint is not None:
            query = query.where(UsageTable.endpoint == endpoint.value)

        results = await postgres_session.execute(query)
        usage_results = results.all()

        usages = []
        for row in usage_results:
            usages.append(
                Usage(
                    model=row.model,
                    key=row.key,
                    endpoint=row.endpoint,
                    created=row.created,
                    usage=UsageDetail(
                        prompt_tokens=row.prompt_tokens,
                        completion_tokens=row.completion_tokens,
                        total_tokens=row.total_tokens,
                        cost=row.cost,
                        carbon=CarbonFootprintUsage(kWh=row.kwh, kgCO2eq=row.kgco2eq),
                        metrics=MetricsUsage(latency=row.latency, ttft=row.ttft),
                    ),
                )
            )

        return usages
