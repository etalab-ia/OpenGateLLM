from api.clients.model.qos_policies import BaseQualityOfServicePolicy


class PerformanceThresholdPolicy(BaseQualityOfServicePolicy):
    def __init__(self, performance_threshold: float | None) -> None:
        super().__init__(
            performance_threshold=performance_threshold,
            max_parallel_requests_shared=None,
            max_parallel_requests_private_shared=None,
            max_parallel_requests_private_private=None,
        )

    def apply_policy(self, performance_indicator: float | None, current_parallel_requests: int | None, threshold_mode: str) -> bool:
        if performance_indicator is not None and performance_indicator > self.performance_threshold:
            return False
        return True
