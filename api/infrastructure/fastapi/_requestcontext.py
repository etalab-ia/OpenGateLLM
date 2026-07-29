from contextvars import ContextVar

from pydantic import BaseModel, ConfigDict

from api.domain.key.entities import Key
from api.domain.user.views import AuthenticatedUserView


class RequestContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    # request identifiers
    id: str | None = None  # @TODO: add request id to usage table
    method: str | None = None
    endpoint: str | None = None

    # user identifiers
    key: Key | None = None
    user: AuthenticatedUserView | None = None
    user_email: str | None = None

    # model identifiers
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


def get_request_context() -> ContextVar[RequestContext]:
    return request_context


def get_authenticated_user() -> AuthenticatedUserView:
    return request_context.get().user
