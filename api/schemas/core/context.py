from typing import Any

from pydantic import BaseModel, ConfigDict

from api.schemas.me import UserInfo
from api.schemas.usage import Usage


class GlobalContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    agent_manager: Any | None = None
    document_manager: Any | None = None
    identity_access_manager: Any | None = None
    limiter: Any | None = None
    model_registry: Any | None = None
    parser_manager: Any | None = None
    tokenizer: Any | None = None


class RequestContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    user_info: UserInfo | None = None
    token_id: int | None = None
    method: str | None = None
    endpoint: str | None = None
    client: str | None = None
    usage: Usage | None = None
