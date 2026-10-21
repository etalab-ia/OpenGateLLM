from datetime import timedelta
import logging

from langfuse import Langfuse, propagate_attributes

from api.domain.usage.entities import UsageRecord

logger = logging.getLogger(__name__)

_KWH_SCORE_COLUMN = "kWh"
_KGCO2EQ_SCORE_COLUMN = "kgCO2eq"


class LangfuseRequestTracer:
    """Traces every model-forward request, failures included. The usage table holds consumption only, so it is the one
    place where a failed request leaves a trace."""

    def __init__(self, client: Langfuse) -> None:
        self.client = client
        self._observation = None

    def start(self, record: UsageRecord) -> None:
        # the SDK takes the start time, the user and the tags only at creation, so the observation starts with the request
        try:
            with propagate_attributes(user_id=str(record.user_id), tags=[f"key_id:{record.key_id}"]):
                self._observation = self.client.start_observation(
                    trace_context={"trace_id": record.request_id},
                    as_type="generation",
                    name=record.endpoint,
                    metadata=self._metadata(record),
                )
        except Exception:
            logger.exception("Failed to start Langfuse observation")
            self._observation = None

    def end(self, record: UsageRecord) -> None:
        if self._observation is None:
            logger.warning("Cannot end Langfuse observation: no active observation (start_observation likely failed)")
            return

        observation, self._observation = self._observation, None
        try:
            observation.update(**self._build_update(record))
            if (usage := record.usage) is not None:
                observation.score(name=_KWH_SCORE_COLUMN, value=usage.impacts.kWh, data_type="NUMERIC")
                observation.score(name=_KGCO2EQ_SCORE_COLUMN, value=usage.impacts.kgCO2eq, data_type="NUMERIC")
        finally:
            # an observation left open is never exported, and the failed request would vanish from Langfuse
            observation.end()

    def _build_update(self, record: UsageRecord) -> dict:
        update: dict = {"model": record.router_name, "metadata": self._metadata(record)}

        if record.status is None or record.status // 100 != 2 or record.error is not None:
            update["level"] = "ERROR"
            update["status_message"] = record.error
        if record.ttft is not None:
            update["completion_start_time"] = record.created + timedelta(milliseconds=record.ttft)
        if (usage := record.usage) is not None:
            update["usage_details"] = {
                # Langfuse sums every "input*" key into inputTokens, so "input" must exclude the cached tokens.
                "input": usage.prompt_tokens - usage.prompt_tokens_details.cached_tokens,
                "output": usage.completion_tokens,
                "input_cached_tokens": usage.prompt_tokens_details.cached_tokens,
            }
            update["cost_details"] = {"total": usage.cost}

        return update

    @staticmethod
    def _metadata(record: UsageRecord) -> dict:
        return {
            "router_id": record.router_id,
            "router_name": record.router_name,
            "user_email": record.user_email,
            "key_id": str(record.key_id),
            "key_name": record.key_name,
            "provider_id": record.provider_id,
            "provider_model_name": record.provider_model_name,
            "status": record.status,
            "latency": record.latency,
        }
