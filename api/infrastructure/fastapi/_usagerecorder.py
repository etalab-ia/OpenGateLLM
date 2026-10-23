from datetime import UTC, datetime

from api.domain.key.entities import Key
from api.domain.usage import UsageContext
from api.domain.usage.entities import Usage, UsageRecord
from api.domain.user.views import AuthenticatedUserView

from ._requesttracer import RequestTracer


class UsageRecorder(UsageContext):
    @classmethod
    def open(
        cls,
        tracer: RequestTracer,
        request_id: str,
        endpoint: str,
        user: AuthenticatedUserView,
        key: Key,
    ) -> "UsageRecorder":
        record = UsageRecord(
            request_id=request_id,
            endpoint=endpoint,
            created=datetime.now(tz=UTC),
            user_id=user.id,
            user_email=user.email,
            key_id=key.id,
            key_name=key.name,
        )
        recorder = cls(tracer=tracer, record=record)
        tracer.start(record)

        return recorder

    def __init__(self, tracer: RequestTracer, record: UsageRecord) -> None:
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

        self.record.status = status_code
        if error is not None:
            self.record.error = error
        if self.record.latency is None:
            self.record.latency = self.elapsed_ms()

        self.tracer.end(self.record)
