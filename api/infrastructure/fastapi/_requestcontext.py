from pydantic import BaseModel, ConfigDict

from api.domain.key.entities import Key
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.fastapi._usagerecorder import UsageRecorder


class RequestContext(BaseModel):
    # arbitrary_types_allowed: UsageRecorder is a plain infrastructure object, not something pydantic can describe
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    # request identifiers
    id: str | None = None
    endpoint: str | None = None
    # name of the exception a 4xx/5xx was mapped from, for the request log line and the usage record
    error: str | None = None

    # user identifiers
    key: Key | None = None
    user: AuthenticatedUserView | None = None

    # opened by the usage dependency of the model-forward routes, closed by RequestLogMiddleware once the response has
    # been sent. It holds everything those requests record: the router, the provider, the tokens, the timings.
    usage_recorder: UsageRecorder | None = None
