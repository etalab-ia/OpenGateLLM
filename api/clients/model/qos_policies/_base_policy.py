from abc import ABC, abstractmethod


class BaseQualityOfServicePolicy(ABC):  # pylint: disable=too-few-public-methods
    """
    Abstract base class for qos policies
    """

    def __init__(
        self,
        performance_threshold: float | None,
        max_parallel_requests: int | None,
    ) -> None:
        self.performance_threshold = performance_threshold
        self.max_parallel_requests = max_parallel_requests

    @abstractmethod
    def apply_policy(self, performance_indicator: float | None, current_parallel_requests: int | None) -> bool:
        pass
