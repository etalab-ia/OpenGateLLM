from datetime import UTC, datetime
import logging

from api.domain.key.entities import Key
from api.domain.usage import UsageContext
from api.domain.usage.entities import Usage, UsageRecord
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.langfuse import LangfuseRequestTracer

logger = logging.getLogger(__name__)


class UsageRecorder(UsageContext):
    @classmethod
    def open(
        cls,
        tracer: LangfuseRequestTracer | None,
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
        recorder = cls(tracer=tracer, record=record)
        if tracer is not None:
            tracer.start(record)

        return recorder

    def __init__(self, tracer: LangfuseRequestTracer | None, record: UsageRecord) -> None:
        self.tracer = tracer
        self.record = record
        self.is_closed = False

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

    def record_error(self, error: str) -> None:
        self.record.error = error

    def get_record(self) -> UsageRecord:
        # a copy, so that closing the request does not change a row already handed to the repository
        return self.record.model_copy(deep=True)

    def close(self, status_code: int | None, error: str | None = None) -> None:
        if self.is_closed:
            return
        self.is_closed = True

        if status_code is not None:
            self.record.status = status_code
        if error is not None:
            self.record.error = error
        if self.record.latency is None:
            self.record.latency = self.elapsed_ms()

        if self.tracer is None:
            return
        try:
            self.tracer.end(self.record)
        except Exception:
            logger.exception("Failed to trace the request.")
