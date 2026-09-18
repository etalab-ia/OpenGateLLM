from datetime import datetime
import logging
from uuid import uuid4

from langfuse import Langfuse, propagate_attributes

from api.domain.usage import UsageRecorder
from api.domain.usage.entities import Usage
from api.infrastructure.fastapi.dependencies import request_context

logger = logging.getLogger(__name__)


class LangfuseUsageRecorder(UsageRecorder):
    def __init__(self, client: Langfuse) -> None:
        self.client = client
        self._observation = None

    def start_record(self, name: str, model: str, user_id: int) -> str:
        try:
            kwargs = {"as_type": "generation", "name": name, "model": model}
            if metadata := self._identity_metadata():
                kwargs["metadata"] = metadata
            with propagate_attributes(user_id=str(user_id)):
                self._observation = self.client.start_observation(**kwargs)
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
                "metadata": {**self._identity_metadata(), "provider_id": provider_id},
            }
            if first_token_at is not None:
                update["completion_start_time"] = first_token_at
            self._observation.update(**update)
            self._observation.score(name="kWh", value=usage.impacts.kWh, data_type="NUMERIC")
            self._observation.score(name="kgCO2eq", value=usage.impacts.kgCO2eq, data_type="NUMERIC")
        except Exception:
            logger.debug("Failed to update Langfuse observation", exc_info=True)

    def fail_record(self, message: str) -> None:
        if self._observation is None:
            return

        try:
            self._observation.update(level="ERROR", status_message=message)
        except Exception:
            logger.debug("Failed to mark Langfuse observation as error", exc_info=True)

    def end_record(self) -> None:
        if self._observation is None:
            return

        try:
            self._observation.end()
        except Exception:
            logger.debug("Failed to end Langfuse observation", exc_info=True)
        finally:
            self._observation = None

    @staticmethod
    def _identity_metadata() -> dict:
        context = request_context.get()
        metadata = {
            "router_id": context.router_id,
            "router_name": context.router_name,
            "provider_model_name": context.provider_model_name,
            "user_email": context.user.email if context.user else None,
            "key_id": context.key.id if context.key else None,
            "key_name": context.key.name if context.key else None,
        }
        return {key: value for key, value in metadata.items() if value is not None}
