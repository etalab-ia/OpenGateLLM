import logging
from typing import TypeVar

from prometheus_client import Counter, Histogram
from prometheus_client.metrics import MetricWrapperBase
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from api.utils.context import request_context

logger = logging.getLogger(__name__)

MetricType = TypeVar("MetricType", bound=MetricWrapperBase)


class MetricsMiddleware:
    """
    ASGI middleware that records LLM-specific Prometheus metrics with a model label.

    Metrics are only recorded for requests where a model was resolved
    (i.e., request_context.router_name is set by the model registry).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app: ASGIApp = app
        self.inference_requests_total: Counter = self.create_metric(
            metric_type=Counter,
            name="inference_requests_total",
            documentation="Total number of LLM requests.",
            label_names=["endpoint", "model", "status_code"],
        )
        self.inference_requests_duration_seconds: Histogram = self.create_metric(
            metric_type=Histogram,
            name="inference_requests_duration_seconds",
            documentation="Duration of LLM requests in seconds.",
            label_names=["endpoint", "model", "status_code"],
        )
        self.inference_ttft_milliseconds: Histogram = self.create_metric(
            metric_type=Histogram,
            name="inference_ttft_milliseconds",
            documentation="Time to first token for streaming LLM responses in milliseconds.",
            label_names=["endpoint", "model", "status_code"],
        )
        self.inference_tokens_total: Counter = self.create_metric(
            metric_type=Counter,
            name="inference_tokens_total",
            documentation="Total number of tokens consumed (prompt and completion).",
            label_names=["endpoint", "model", "type"],
        )

    @staticmethod
    def create_metric(metric_type: type[MetricType], name: str, documentation: str, label_names: list[str] | None = None) -> MetricType:
        """
        Create a Prometheus metric of the specified type.

        Args:
            metric_type (type[MetricType]): The Prometheus metric class to instantiate (e.g., Counter, Histogram). This should be a subclass of prometheus_client.metrics.MetricWrapperBase.
            name (str): The name of the metric.
            documentation (str): A description of the metric for Prometheus.
            label_names (list[str], optional): A list of label names for the metric. Defaults to None.

        Returns:
        MetricType: An instance of the created Prometheus metric (Counter, Histogram, etc.). The specific type depends on the metric_type argument provided. Compatible with any metric class from prometheus_client.metrics that inherits from MetricWrapperBase.
        """
        if label_names is None:
            label_names = []
        return metric_type(name, documentation, label_names)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            try:
                context = request_context.get()
                model = context.router_name
                endpoint = context.endpoint

                if model and endpoint:
                    self.inference_requests_total.labels(
                        endpoint=endpoint,
                        model=model,
                        status_code=str(status_code),
                    ).inc()

                    latency = context.latency
                    if latency is not None:
                        self.inference_requests_duration_seconds.labels(
                            endpoint=endpoint,
                            model=model,
                            status_code=str(status_code),
                        ).observe(latency / 1000)

                    ttft = context.ttft
                    if ttft is not None:
                        self.inference_ttft_milliseconds.labels(endpoint=endpoint, model=model, status_code=str(status_code)).observe(ttft)

                    usage = context.usage
                    if usage is not None:
                        if usage.prompt_tokens:
                            self.inference_tokens_total.labels(
                                endpoint=endpoint,
                                model=model,
                                type="prompt",
                            ).inc(usage.prompt_tokens)
                        if usage.completion_tokens:
                            self.inference_tokens_total.labels(
                                endpoint=endpoint,
                                model=model,
                                type="completion",
                            ).inc(usage.completion_tokens)
            except Exception:
                pass
