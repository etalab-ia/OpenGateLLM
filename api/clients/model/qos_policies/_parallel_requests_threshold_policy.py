from api.clients.model.qos_policies import BaseQualityOfServicePolicy
from api.schemas.core.configuration import ThresholdMode


class ParallelRequestsThresholdPolicy(BaseQualityOfServicePolicy):
    def __init__(
        self,
        max_parallel_requests_shared: int | None,
        max_parallel_requests_private_shared: int | None,
        max_parallel_requests_private_private: int | None,
    ) -> None:
        super().__init__(
            performance_threshold=None,
            max_parallel_requests_shared=max_parallel_requests_shared,
            max_parallel_requests_private_shared=max_parallel_requests_private_shared,
            max_parallel_requests_private_private=max_parallel_requests_private_private,
        )

    def apply_policy(self, performance_indicator: float | None, current_parallel_requests: int | None, threshold_mode: str) -> bool:
        if threshold_mode == ThresholdMode.SHARED:
            max_parallel_requests = self.max_parallel_requests_shared
        elif threshold_mode == ThresholdMode.PRIVATE_SHARED:
            max_parallel_requests = self.max_parallel_requests_private_shared
        else:
            max_parallel_requests = self.max_parallel_requests_private_private
        if current_parallel_requests is not None and current_parallel_requests > max_parallel_requests:
            return False
        return True
