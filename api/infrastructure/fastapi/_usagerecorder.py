import asyncio
from datetime import UTC, datetime
import logging

from api.domain.key.entities import Key
from api.domain.usage import UsageContext, UsageRepository
from api.domain.usage.entities import Usage, UsageRecord
from api.domain.user.views import AuthenticatedUserView

logger = logging.getLogger(__name__)

# asyncio only holds a weak reference to a running task, so an unreferenced one may be collected mid-flight
_pending_saves: set[asyncio.Task] = set()


class UsageRecorder(UsageContext):
    """One request's usage record. The HTTP layer opens it before the use case runs and closes it once the response
    has been sent, which is the only moment the answered status and the real duration are both known. In between the
    use case fills in what it alone knows, through the narrower `UsageContext` port."""

    @classmethod
    def open(
        cls,
        usage_repository: UsageRepository,
        request_id: str,
        endpoint: str,
        user: AuthenticatedUserView | None,
        key: Key | None,
    ) -> "UsageRecorder":
        record = UsageRecord(
            request_id=request_id,
            endpoint=endpoint,
            created=datetime.now(tz=UTC),
            user_id=user.id if user else None,
            user_email=user.email if user else None,
            key_id=key.id if key else None,
            key_name=key.name if key else None,
        )
        recorder = cls(usage_repository=usage_repository, record=record)
        usage_repository.open_record(record)

        return recorder

    def __init__(self, usage_repository: UsageRepository, record: UsageRecord) -> None:
        self.usage_repository = usage_repository
        self.record = record
        self.is_closed = False

    # UsageContext — what the use case records
    def get_request_id(self) -> str:
        return self.record.request_id

    def elapsed_ms(self, at: datetime | None = None) -> int:
        return round(((at or datetime.now(tz=UTC)) - self.record.created).total_seconds() * 1000)

    def record_router(self, router_id: int, router_name: str) -> None:
        self.record.router_id = router_id
        self.record.router_name = router_name

    def record_provider(self, provider_id: int, provider_model_name: str) -> None:
        self.record.provider_id = provider_id
        self.record.provider_model_name = provider_model_name

    def record_usage(self, usage: Usage, latency: int, ttft: int | None = None) -> None:
        self.record.usage = usage
        self.record.latency = latency
        if ttft is not None:
            self.record.ttft = ttft

    # HTTP layer — the lifecycle
    def close(self, status_code: int | None, error: str | None = None) -> None:
        if self.is_closed:
            return
        self.is_closed = True

        if status_code is not None:
            self.record.status = status_code
        self.record.error = error
        if self.record.latency is None:
            # the request never reached the provider: what an incident needs is how long it took to fail
            self.record.latency = self.elapsed_ms()

        task = asyncio.create_task(self._save(), name=f"usage-save-{self.record.request_id}")
        _pending_saves.add(task)
        task.add_done_callback(_pending_saves.discard)

    async def _save(self) -> None:
        try:
            await self.usage_repository.save_record(self.record)
        except Exception:
            logger.exception("Failed to save the usage record.")

    @staticmethod
    async def wait_for_pending_saves(timeout: float) -> None:
        if not _pending_saves:
            return

        _, unfinished = await asyncio.wait(tuple(_pending_saves), timeout=timeout)
        if unfinished:
            logger.warning(f"{len(unfinished)} usage records were still being saved at shutdown and are lost.")
