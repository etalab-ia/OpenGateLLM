from typing import Any

from pydantic import BaseModel, ConfigDict

from api.schemas.me.info import UserInfo
from api.schemas.usage import Usage


class GlobalContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    # TODO: replace Any with specific types
    document_manager: Any | None = None
    identity_access_manager: Any | None = None
    limiter: Any | None = None
    usage_manager: Any | None = None
    model_registry: Any | None = None
    parser_manager: Any | None = None
    tokenizer: Any | None = None
    redis_pool: Any | None = None
    postgres_session_factory: Any | None = None


class RequestContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    # request identifiers
    id: str | None = None
    method: str | None = None
    endpoint: str | None = None

    # request context
    user_info: UserInfo | None = None
    key_id: int | None = None
    key_name: str | None = None
    router_id: int | None = None
    provider_id: int | None = None

    # request body
    router_name: str | None = None
    provider_model_name: str | None = None

    # response
    usage: Usage | None = None
    ttft: int | None = None
    latency: int | None = None
