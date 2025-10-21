from abc import ABC, abstractmethod


class BaseQualityOfServicePolicy(ABC):  # pylint: disable=too-few-public-methods
    """
    Abstract base class for qos policies
    """

    def __init__(
        self,
        performance_threshold: float | None,
        max_parallel_requests_shared: int | None,
        max_parallel_requests_private_shared: int | None,
        max_parallel_requests_private_private: int | None,
    ) -> None:
        self.performance_threshold = performance_threshold
        self.max_parallel_requests_shared = max_parallel_requests_shared
        self.max_parallel_requests_private_shared = max_parallel_requests_private_shared
        self.max_parallel_requests_private_private = max_parallel_requests_private_private

    @abstractmethod
    def apply_policy(self, performance_indicator: float | None, current_parallel_requests: int | None, threshold_mode: str) -> bool:
        pass
