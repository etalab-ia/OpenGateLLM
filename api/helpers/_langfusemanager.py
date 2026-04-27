from enum import StrEnum
import logging
from typing import Any

from langfuse import Langfuse, propagate_attributes

from api.utils.context import request_context

logger = logging.getLogger(__name__)


class ObservationName(StrEnum):
    AUDIO_TRANSCRIPTIONS = "audio-transcriptions"
    CHAT_COMPLETIONS = "chat-completions"
    EMBEDDINGS = "embeddings"
    OCR = "ocr"
    PARSE = "parse"
    RERANK = "rerank"
    SEARCH = "search"


class LangfuseManager:
    def __init__(self, client: Langfuse):
        self._client = client

    def start_observation(self, as_type: str, name: str | None = None, model: str | None = None) -> Any:
        """Start a new observation in the current trace context.

        Args:
            as_type: The type of observation ("span" or "generation").
            name: Optional name for the observation.
            model: Optional model name (for generation observations).

        Returns:
            The Langfuse observation object.
        """
        ctx = request_context.get()
        trace_context = {"trace_id": ctx.langfuse_trace_id, "parent_span_id": ctx.langfuse_parent_span_id} if ctx.langfuse_trace_id else None

        kwargs: dict[str, Any] = {"as_type": as_type}
        if name is not None:
            kwargs["name"] = name
        if model is not None:
            kwargs["model"] = model
        if trace_context is not None:
            kwargs["trace_context"] = trace_context

        if ctx.user_info is not None:
            with propagate_attributes(user_id=str(ctx.user_info.email)):
                return self._client.start_observation(**kwargs)
        return self._client.start_observation(**kwargs)

    @staticmethod
    def update_observation(
        langfuse_obs,
        *,
        usage_details: dict[str, int] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Update an observation with output, usage details, or metadata. Swallows Langfuse errors so tracing failures never break the request."""
        kwargs: dict[str, Any] = {}
        if usage_details is not None:
            kwargs["usage_details"] = usage_details
        if metadata is not None:
            kwargs["metadata"] = metadata
        if not kwargs:
            return

        try:
            langfuse_obs.update(**kwargs)
        except Exception as e:
            logger.debug(f"Failed to update Langfuse observation: {e}", exc_info=True)

    @staticmethod
    def end_observation(langfuse_obs) -> None:
        """End an observation. Swallows Langfuse errors so tracing failures never break the request."""
        try:
            langfuse_obs.end()
        except Exception as e:
            logger.debug(f"Failed to end Langfuse observation: {e}", exc_info=True)

    @staticmethod
    def end_root_observation(langfuse_obs, status: int | None) -> None:
        """Update the root span with request metadata and end it. Works for both streaming and non-streaming responses."""
        try:
            ctx = request_context.get()
            metadata = {
                "status": status,
                "router_name": ctx.router_name,
                "provider_model_name": ctx.provider_model_name,
                "latency_ms": ctx.latency,
                "cost": ctx.usage.cost if ctx.usage else None,
            }
            if ctx.ttft is not None:
                metadata["ttft_ms"] = ctx.ttft
            langfuse_obs.update(metadata=metadata)
        except Exception as e:
            logger.debug(f"Failed to update Langfuse root observation: {e}", exc_info=True)
        finally:
            langfuse_obs.end()
