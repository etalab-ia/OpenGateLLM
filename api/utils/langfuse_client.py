import logging
import os

logger = logging.getLogger(__name__)

_langfuse = None
_initialized = False


def get_langfuse_client():
    """
    Returns the Langfuse client singleton if LANGFUSE_SECRET_KEY and LANGFUSE_PUBLIC_KEY
    environment variables are set, otherwise returns None.

    The client is initialized once and reused across requests.
    """
    global _langfuse, _initialized
    if _initialized:
        return _langfuse
    _initialized = True

    if not os.getenv("LANGFUSE_SECRET_KEY") or not os.getenv("LANGFUSE_PUBLIC_KEY"):
        return None

    try:
        from langfuse import get_client

        _langfuse = get_client()
        logger.info("Langfuse tracing initialized.")
    except ImportError:
        logger.warning("langfuse package not installed. LLM tracing disabled. Install with: pip install langfuse")
    except Exception as e:
        logger.warning(f"Failed to initialize Langfuse client: {e}")

    return _langfuse
