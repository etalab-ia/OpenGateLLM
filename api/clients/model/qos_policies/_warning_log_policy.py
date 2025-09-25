import logging
from api.clients.model.qos_policies import BaseQualityOfServicePolicy

logger = logging.getLogger(__name__)


class WarningLogPolicy(BaseQualityOfServicePolicy):
    def apply_policy(self, performance_indicator: float | None, current_parallel_requests: int | None) -> bool:
        if performance_indicator is not None and performance_indicator > self.performance_threshold:
            logger.warning(
                "Performance indicator exceeds threshold (%s > %s)",
                performance_indicator,
                self.performance_threshold,
            )
        if current_parallel_requests is not None and current_parallel_requests > self.max_parallel_requests:
            logger.warning(
                "Too many requests waiting for vllm response: %s, %s max",
                current_parallel_requests,
                self.max_parallel_requests,
            )

        return True
