from pydantic import BaseModel, ConfigDict

from api.domain.key.entities import Key
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.fastapi._usagerecorder import UsageRecorder


class RequestContext(BaseModel):
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    # request identifiers
    id: str | None = None
    endpoint: str | None = None
    error: str | None = None

    # user identifiers
    key: Key | None = None
    user: AuthenticatedUserView | None = None

    usage_recorder: UsageRecorder | None = None
