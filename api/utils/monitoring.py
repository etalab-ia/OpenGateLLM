from collections.abc import Callable

from prometheus_client import Counter, Histogram
from prometheus_fastapi_instrumentator.metrics import Info

from api.utils.context import request_context


def _build_metric_name(namespace: str, name: str) -> str:
    return f"{namespace}_{name}" if namespace else name


def inference_requests_total(metric_namespace: str = "") -> Callable[[Info], None]:
    metric_name = _build_metric_name(metric_namespace, "inference_requests_total")
    metric = Counter(
        metric_name,
        "Total number of LLM requests.",
        labelnames=("endpoint", "model", "status_code"),
    )

    def instrumentation(info: Info) -> None:
        try:
            context = request_context.get()
            model = context.router_name
            endpoint = context.endpoint
            if model and endpoint:
                metric.labels(endpoint=endpoint, model=model, status_code=info.modified_status).inc()
        except Exception:
            pass

    return instrumentation


def inference_requests_duration_seconds(metric_namespace: str = "") -> Callable[[Info], None]:
    metric_name = _build_metric_name(metric_namespace, "inference_requests_duration_seconds")
    metric = Histogram(
        metric_name,
        "Duration of LLM requests in seconds.",
        labelnames=("endpoint", "model", "status_code"),
        buckets=(
            0.05,
            0.1,
            0.2,
            0.3,
            0.4,
            0.5,
            0.75,
            1,
            1.5,
            2,
            2.5,
            3,
            3.5,
            4,
            4.5,
            5,
            6,
            7,
            8,
            9,
            10,
            15,
            20,
            25,
            30,
            45,
            60,
            75,
            90,
            105,
            120,
            150,
            180,
            210,
            240,
            270,
            300,
        ),
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


def inference_ttft_milliseconds(metric_namespace: str = "") -> Callable[[Info], None]:
    metric_name = _build_metric_name(metric_namespace, "inference_ttft_milliseconds")
    metric = Histogram(
        metric_name,
        "Time to first token for streaming LLM responses in milliseconds.",
        labelnames=("endpoint", "model", "status_code"),
        buckets=(
            5,
            10,
            20,
            30,
            50,
            75,
            100,
            150,
            200,
            300,
            500,
            750,
            1000,
            1500,
            2000,
            3000,
            5000,
            7500,
            10000,
            15000,
            20000,
            25000,
            30000,
            45000,
            60000,
            75000,
            90000,
            105000,
            120000,
            135000,
            150000,
            165000,
            180000,
            210000,
            240000,
            270000,
            300000,
        ),
    )

    def instrumentation(info: Info) -> None:
        try:
            context = request_context.get()
            model = context.router_name
            endpoint = context.endpoint
            ttft = context.ttft
            if model and endpoint and ttft is not None:
                metric.labels(endpoint=endpoint, model=model, status_code=info.modified_status).observe(ttft)
        except Exception:
            pass

    return instrumentation


def inference_output_tokens_per_second(metric_namespace: str = "") -> Callable[[Info], None]:
    metric_name = _build_metric_name(metric_namespace, "inference_output_tokens_per_second")
    metric = Histogram(
        metric_name,
        "Output generation speed in tokens per second (completion tokens / request duration, TTFT included).",
        labelnames=("endpoint", "model"),
        buckets=(5, 10, 20, 30, 50, 75, 85, 90, 95, 100, 105, 110, 115, 125, 150, 175, 200, 250, 300, 400, 500, 750, 1000),
    )

    def instrumentation(info: Info) -> None:
        try:
            context = request_context.get()
            model = context.router_name
            endpoint = context.endpoint
            usage = context.usage
            latency = context.latency
            if model and endpoint and usage and latency and usage.completion_tokens:
                metric.labels(endpoint=endpoint, model=model).observe(usage.completion_tokens / (latency / 1000))
        except Exception:
            pass

    return instrumentation


def inference_tokens_total(metric_namespace: str = "") -> Callable[[Info], None]:
    metric_name = _build_metric_name(metric_namespace, "inference_tokens_total")
    metric = Counter(
        metric_name,
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
