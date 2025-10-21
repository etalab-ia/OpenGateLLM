import logging

from api.clients.model.qos_policies import BaseQualityOfServicePolicy
from api.schemas.core.configuration import ThresholdMode

logger = logging.getLogger(__name__)


class WarningLogPolicy(BaseQualityOfServicePolicy):
    def apply_policy(self, performance_indicator: float | None, current_parallel_requests: int | None, threshold_mode: str) -> bool:
        if performance_indicator is not None and performance_indicator > self.performance_threshold:
            logger.warning(
                "Performance indicator exceeds threshold (%s > %s)",
                performance_indicator,
                self.performance_threshold,
            )
        if threshold_mode == ThresholdMode.SHARED:
            max_parallel_requests = self.max_parallel_requests_shared
        elif threshold_mode == ThresholdMode.PRIVATE_SHARED:
            max_parallel_requests = self.max_parallel_requests_private_shared
        else:
            max_parallel_requests = self.max_parallel_requests_private_private
        if current_parallel_requests is not None and current_parallel_requests > max_parallel_requests:
            logger.warning(
                "Too many requests waiting for vllm response: %s, %s max in %s mode",
                current_parallel_requests,
                max_parallel_requests,
                threshold_mode,
            )

        return True
