from collections.abc import AsyncGenerator, Callable
from datetime import UTC, datetime
from http import HTTPMethod
import logging
from typing import Any
from uuid import uuid4

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.usage import UsageRecorder
from api.domain.usage.entities import Usage
from api.sql.models import Usage as UsageTable
from api.utils.configuration import configuration
from api.utils.variables import EndpointRoute

logger = logging.getLogger(__name__)
PostgresSessionProvider = Callable[[], AsyncGenerator[AsyncSession | Any, Any]]


class PostgresUsageRecorder(UsageRecorder):
    def __init__(self, background_tasks: BackgroundTasks, postgres_session_provider: PostgresSessionProvider) -> None:
        self.background_tasks = background_tasks
        self.postgres_session_provider = postgres_session_provider
        self._row: UsageTable | None = None

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
        self._row = UsageTable(
            created=datetime.now(tz=UTC),
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
        if self._row is None:
            return

        self._row.provider_id = provider_id
        self._row.provider_model_name = provider_model_name
        self._row.prompt_tokens = usage.prompt_tokens
        self._row.completion_tokens = usage.completion_tokens
        self._row.total_tokens = usage.total_tokens
        self._row.cost = usage.cost
        self._row.kwh = usage.impacts.kWh
        self._row.kgco2eq = usage.impacts.kgCO2eq
        self._row.status = 200

    def fail_record(self, message: str) -> None:
        return

    def end_record(self) -> None:
        row = self._row
        self._row = None
        if row is None:
            return
        self.background_tasks.add_task(self._persist, row)

    async def _persist(self, row: UsageTable) -> None:
        if configuration.settings.monitoring_postgres_enabled is False:
            return
        try:
            async for postgres_session in self.postgres_session_provider():
                postgres_session.add(row)
                try:
                    await postgres_session.commit()
                except Exception as e:
                    logger.error("Failed to log usage: %s", e)
                    await postgres_session.rollback()
        except RuntimeError as e:
            logger.warning("Skipping usage logging because postgres session is unavailable: %s", e)
        except Exception:
            logger.exception("Unexpected failure during usage logging.")
