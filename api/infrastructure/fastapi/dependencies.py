from contextvars import ContextVar

from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.fastapi._requestcontext import RequestContext

request_context: ContextVar[RequestContext] = ContextVar("request_context", default=RequestContext())


def get_request_context() -> ContextVar[RequestContext]:
    return request_context


def get_authenticated_user() -> AuthenticatedUserView:
    return request_context.get().user
