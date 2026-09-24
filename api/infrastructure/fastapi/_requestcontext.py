from pydantic import BaseModel, ConfigDict

from api.domain.key.entities import Key
from api.domain.usage.entities import Usage
from api.domain.user.views import AuthenticatedUserView


class RequestContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    # request identifiers
    id: str | None = None
    endpoint: str | None = None

    # user identifiers
    key: Key | None = None
    user: AuthenticatedUserView | None = None

    # model identifiers
    router_id: int | None = None
    provider_id: int | None = None
    router_name: str | None = None
    provider_model_name: str | None = None

    # usage — carried whole so the row builder reads one recorded object instead of a flat mirror that drifts
    usage: Usage | None = None
