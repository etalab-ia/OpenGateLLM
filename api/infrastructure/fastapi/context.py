from contextvars import ContextVar

from pydantic import BaseModel, ConfigDict


class RequestContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    # request identifiers
    id: str | None = None
    method: str | None = None
    endpoint: str | None = None

    # request context
    user_id: int | None = None
    user_email: str | None = None
    key_id: int | None = None
    key_name: str | None = None  # @TODO: refactor key repository to implement this field
    router_id: int | None = None
    provider_id: int | None = None
    router_name: str | None = None
    provider_model_name: str | None = None

    # usage
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cost: float | None = None
    kwh: float | None = None
    kgco2eq: float | None = None


request_context: ContextVar[RequestContext] = ContextVar("request_context", default=RequestContext())
