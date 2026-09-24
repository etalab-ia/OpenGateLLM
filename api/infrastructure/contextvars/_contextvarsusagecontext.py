from contextvars import ContextVar

from api.domain.usage import UsageContext
from api.domain.usage.entities import Usage
from api.infrastructure.fastapi import RequestContext


class ContextVarsUsageContext(UsageContext):
    def __init__(self, request_context: ContextVar[RequestContext]) -> None:
        self.request_context = request_context

    @property
    def request_id(self) -> str:
        request_id = self.request_context.get().id
        if request_id is None:
            raise RuntimeError("request_id missing from RequestContext")
        return request_id

    def record_router(self, router_id: int, router_name: str) -> None:
        context = self.request_context.get()
        context.router_id = router_id
        context.router_name = router_name

    def record_provider(self, provider_id: int, provider_model_name: str) -> None:
        context = self.request_context.get()
        context.provider_id = provider_id
        context.provider_model_name = provider_model_name

    def record_usage(self, usage: Usage) -> None:
        self.request_context.get().usage = usage
