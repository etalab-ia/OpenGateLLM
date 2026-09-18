from datetime import datetime
import logging
from uuid import uuid4

from langfuse import Langfuse, propagate_attributes

from api.domain.usage import UsageRecorder
from api.domain.usage.entities import Usage

logger = logging.getLogger(__name__)


class LangfuseUsageRecorder(UsageRecorder):
    def __init__(self, client: Langfuse):
        self.client = client
        self._observation = None

    def start_record(self, name: str, model: str, user_id: int) -> str:
        try:
            with propagate_attributes(user_id=str(user_id)):
                self._observation = self.client.start_observation(as_type="generation", name=name, model=model)
            return self._observation.trace_id
        except Exception:
            logger.error("Failed to start Langfuse observation", exc_info=True)
            self._observation = None
            return uuid4().hex

    def update_record(self, usage: Usage, provider_id: int, first_token_at: datetime | None = None) -> None:
        if self._observation is None:
            return

        try:
            update = {
                "usage_details": {
                    "input": usage.prompt_tokens,
                    "output": usage.completion_tokens,
                    "input_cached_tokens": usage.prompt_tokens_details.cached_tokens,
                },
                "cost_details": {"total": usage.cost},
                "metadata": {"kWh": usage.impacts.kWh, "kgCO2eq": usage.impacts.kgCO2eq, "provider_id": provider_id},
            }
            if first_token_at is not None:
                update["completion_start_time"] = first_token_at
            self._observation.update(**update)
        except Exception:
            logger.debug("Failed to update Langfuse observation", exc_info=True)

    def end_record(self) -> None:
        if self._observation is None:
            return

        try:
            self._observation.end()
        except Exception:
            logger.debug("Failed to end Langfuse observation", exc_info=True)
        finally:
            self._observation = None
