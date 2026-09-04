from contextvars import ContextVar

from api.domain.usage import UsageRecorder

from ._requestcontext import RequestContext


class RequestContextUsageRecorder(UsageRecorder):
    def __init__(self, request_context: ContextVar[RequestContext]) -> None:
        self.request_context = request_context

    def record_router(self, router_id: int, router_name: str) -> None:
        context = self.request_context.get()
        context.router_id = router_id
        context.router_name = router_name

    def record_provider(self, provider_id: int, provider_model_name: str) -> None:
        context = self.request_context.get()
        context.provider_id = provider_id
        context.provider_model_name = provider_model_name

    def record_usage(self, request_id: str | None, prompt_tokens: int, completion_tokens: int, cost: float) -> None:
        context = self.request_context.get()
        context.id = request_id
        context.prompt_tokens = prompt_tokens
        context.completion_tokens = completion_tokens
        context.cost = cost
