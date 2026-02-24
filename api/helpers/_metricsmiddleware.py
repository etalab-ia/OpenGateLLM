from collections.abc import Callable

from prometheus_client import Counter, Histogram
from prometheus_fastapi_instrumentator.metrics import Info

from api.utils.context import request_context


def inference_requests_total() -> Callable[[Info], None]:
    metric = Counter(
        "inference_requests_total",
        "Total number of LLM requests.",
        labelnames=("endpoint", "model", "status_code"),
    )

    def instrumentation(info: Info) -> None:
        try:
            context = request_context.get()
            model = context.router_name
            endpoint = context.endpoint
            if model and endpoint:
                metric.labels(
                    endpoint=endpoint,
                    model=model,
                    status_code=info.modified_status,
                ).inc()
        except Exception:
            pass

    return instrumentation


def inference_requests_duration_seconds() -> Callable[[Info], None]:
    metric = Histogram(
        "inference_requests_duration_seconds",
        "Duration of LLM requests in seconds.",
        labelnames=("endpoint", "model", "status_code"),
    )

    def instrumentation(info: Info) -> None:
        try:
            context = request_context.get()
            model = context.router_name
            endpoint = context.endpoint
            latency = context.latency
            if model and endpoint and latency is not None:
                metric.labels(
                    endpoint=endpoint,
                    model=model,
                    status_code=info.modified_status,
                ).observe(latency / 1000)
        except Exception:
            pass

    return instrumentation


def inference_ttft_milliseconds() -> Callable[[Info], None]:
    metric = Histogram(
        "inference_ttft_milliseconds",
        "Time to first token for streaming LLM responses in milliseconds.",
        labelnames=("endpoint", "model", "status_code"),
    )

    def instrumentation(info: Info) -> None:
        try:
            context = request_context.get()
            model = context.router_name
            endpoint = context.endpoint
            ttft = context.ttft
            if model and endpoint and ttft is not None:
                metric.labels(
                    endpoint=endpoint,
                    model=model,
                    status_code=info.modified_status,
                ).observe(ttft)
        except Exception:
            pass

    return instrumentation


def inference_tokens_total() -> Callable[[Info], None]:
    metric = Counter(
        "inference_tokens_total",
        "Total number of tokens consumed (prompt and completion).",
        labelnames=("endpoint", "model", "type"),
    )

    def instrumentation(info: Info) -> None:
        try:
            context = request_context.get()
            model = context.router_name
            endpoint = context.endpoint
            usage = context.usage
            if model and endpoint and usage is not None:
                if usage.prompt_tokens:
                    metric.labels(endpoint=endpoint, model=model, type="prompt").inc(usage.prompt_tokens)
                if usage.completion_tokens:
                    metric.labels(endpoint=endpoint, model=model, type="completion").inc(usage.completion_tokens)
        except Exception:
            pass

    return instrumentation
