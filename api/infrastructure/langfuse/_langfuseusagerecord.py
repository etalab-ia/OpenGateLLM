from datetime import UTC, datetime
import logging
from uuid import uuid4

from langfuse import Langfuse, propagate_attributes

from api.domain.provider.entities import ProviderEndpoint
from api.domain.usage import UsageRecorder
from api.domain.usage.entities import Usage

logger = logging.getLogger(__name__)


class LangfuseUsageRecorder(UsageRecorder):
    def __init__(self, client: Langfuse) -> None:
        self.client = client
        self.start_time: datetime | None = None
        self._observation = None
        self._metadata: dict = {}

    def start_record(
        self,
        endpoint: ProviderEndpoint,
        model: str,
        user_id: int,
        router_id: int,
        router_name: str,
        user_email: str,
        key_id: int,
        key_name: str,
    ) -> str:
        self.start_time = datetime.now(tz=UTC)
        self._metadata = {"router_id": router_id, "router_name": router_name, "user_email": user_email, "key_id": key_id, "key_name": key_name}
        try:
            with propagate_attributes(user_id=str(user_id)):
                self._observation = self.client.start_observation(
                    as_type="generation",
                    name=endpoint.strip("/").replace("/", "-"),
                    model=model,
                    metadata=self._metadata,
                )
            return self._observation.trace_id
        except Exception:
            logger.exception("Failed to start Langfuse observation")
            self._observation = None
            self._metadata = {}
            return uuid4().hex

    def update_record(self, usage: Usage, provider_id: int, provider_model_name: str, first_token_at: datetime | None = None) -> None:
        if self._observation is None:
            return

        try:
            self._metadata["provider_model_name"] = provider_model_name
            self._metadata["provider_id"] = provider_id
            update = {
                "usage_details": {
                    "input": usage.prompt_tokens,
                    "output": usage.completion_tokens,
                    "input_cached_tokens": usage.prompt_tokens_details.cached_tokens,
                },
                "cost_details": {"total": usage.cost},
                "metadata": self._metadata,
            }
            if first_token_at is not None:
                update["completion_start_time"] = first_token_at
            self._observation.update(**update)
            self._observation.score(name="kWh", value=usage.impacts.kWh, data_type="NUMERIC")
            self._observation.score(name="kgCO2eq", value=usage.impacts.kgCO2eq, data_type="NUMERIC")
        except Exception:
            logger.exception("Failed to update Langfuse observation")

    def fail_record(self, message: str, status_code: int) -> None:
        if self._observation is None:
            return

        try:
            self._observation.update(level="ERROR", status_message=message)
        except Exception:
            logger.exception("Failed to mark Langfuse observation as error")

    def compute_latency(self, end_time: datetime | None = None) -> int:
        if self.start_time is None:
            return 0

        return round(((end_time or datetime.now(tz=UTC)) - self.start_time).total_seconds() * 1000)

    def end_record(self) -> None:
        if self._observation is None:
            return

        try:
            self._observation.end()
        except Exception:
            logger.exception("Failed to end Langfuse observation")
        finally:
            self._observation = None
            self._metadata = {}
