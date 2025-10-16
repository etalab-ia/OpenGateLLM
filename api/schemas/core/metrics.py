from enum import Enum


class MetricType(str, Enum):
    TTFT = "ttft"  # time to first token
    LATENCY = "latency"  # requests latency
    INFLIGHT = "inflight"  # requests concurrency
    PERFORMANCE = "performance"  # custom performance metric
