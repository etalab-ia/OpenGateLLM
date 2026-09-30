from fastapi import BackgroundTasks
from pydantic import BaseModel, ConfigDict

from api.domain.key.entities import Key
from api.domain.usage.entities import Usage
from api.domain.user.views import AuthenticatedUserView


class RequestContext(BaseModel):
    # arbitrary_types_allowed: BackgroundTasks is a plain FastAPI object, not something pydantic can describe
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    # request identifiers
    id: str | None = None
    endpoint: str | None = None
    # name of the exception a 4xx/5xx was mapped from, for the request log line
    error: str | None = None

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

    # FastAPI only runs its BackgroundTasks on the response the route handler returns, so a raised exception drops the
    # queued usage row. RequestLogMiddleware reads this to attach the queue to the 500 it builds instead.
    background_tasks: BackgroundTasks | None = None
