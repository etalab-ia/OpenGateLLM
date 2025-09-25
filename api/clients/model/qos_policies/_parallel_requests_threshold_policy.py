from api.clients.model.qos_policies import BaseQualityOfServicePolicy


class ParallelRequestsThresholdPolicy(BaseQualityOfServicePolicy):
    def __init__(self, max_parallel_requests: int | None) -> None:
        super().__init__(performance_threshold=None, max_parallel_requests=max_parallel_requests)

    def apply_policy(self, performance_indicator: float | None, current_parallel_requests: int | None) -> bool:
        if current_parallel_requests is not None and current_parallel_requests > self.max_parallel_requests:
            return False
        return True
