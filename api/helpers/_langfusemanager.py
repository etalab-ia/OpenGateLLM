from enum import StrEnum
import logging
from typing import Any

from langfuse import Langfuse

from api.schemas.core.configuration import LangfuseDependency
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
    def __init__(self, config: LangfuseDependency):
        self._client = Langfuse(
            public_key=config.public_key,
            secret_key=config.secret_key,
            host=config.url,
        )

        if not self._client.auth_check():
            logger.warning("Cannot connect to Langfuse. Check your langfuse dependency configuration (public_key, secret_key, url).")
            return
        logger.info("Langfuse client successfully connected.")

    def start_observation(self, as_type: str, name: str | None = None, model: str | None = None, input: Any = None) -> Any:
        """Start a new observation in the current trace context.

        Args:
            as_type: The type of observation ("span" or "generation").
            name: Optional name for the observation.
            model: Optional model name (for generation observations).
            input: Optional input data to attach to the observation.

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
        if input is not None:
            kwargs["input"] = input

        return self._client.start_observation(**kwargs)

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


# TODO - Add userId in traces to track users
# TODO - When using a file/picture, please add the document type as metadata and document size
