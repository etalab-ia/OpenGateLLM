from pydantic import BaseModel, ConfigDict

from api.schemas.me.info import UserInfo


class RequestContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    # request identifiers
    id: str | None = None
    method: str | None = None
    endpoint: str | None = None

    # request context
    user_info: UserInfo | None = None
    user_id: int | None = None
    key_id: int | None = None
    key_name: str | None = None
