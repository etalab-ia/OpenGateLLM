import logging
from time import perf_counter

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from api.infrastructure.fastapi._requestcontext import RequestContext
from api.infrastructure.fastapi.dependencies import request_context
from api.infrastructure.fastapi.endpoints.exceptions import InternalServerHTTPException

# A stable name rather than __name__: log collectors and log_config files select this stream by it, and a module path
# would move with every rename of this file.
logger = logging.getLogger("api.request")


class RequestLogMiddleware:
    """Writes one log line per request, with who made it, and turns any exception no endpoint mapped into the generic 500.

    It replaces the uvicorn access log, which knows neither the user nor the duration.

    The exception is swallowed rather than handled by an exception handler registered on Exception: Starlette calls such
    a handler and then re-raises, so uvicorn would log the same traceback a second time.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started_at = perf_counter()
        status_code = None

        async def send_tracking_status(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_tracking_status)
        except Exception:
            # The status line is already sent: a 500 can no longer be answered, let the server log and close the connection.
            if status_code is not None:
                raise

            logger.exception("Unhandled exception while processing request", extra=self._request_fields(scope, request_context.get()))
            status_code = InternalServerHTTPException.status_code
            response = JSONResponse(status_code=status_code, content={"detail": InternalServerHTTPException.detail})
            await response(scope, receive, send)
        finally:
            # finally: a client disconnect (CancelledError) or a failure mid-stream still gets its line.
            duration_ms = round((perf_counter() - started_at) * 1000, 1)
            logger.info(
                "%s %s %s %.1fms",
                scope["method"],
                scope["path"],
                status_code,
                duration_ms,
                extra={**self._request_fields(scope, request_context.get()), "status_code": status_code, "duration_ms": duration_ms},
            )

    @staticmethod
    def _request_fields(scope: Scope, context: RequestContext) -> dict:
        client = scope.get("client")
        # Set by the router once a route matches, so absent on a 404. A mounted ASGI app is an instance, not a function.
        handler = scope.get("endpoint")
        optional_fields = {
            "handler": f"{handler.__module__}.{getattr(handler, '__qualname__', type(handler).__qualname__)}" if handler else None,
            "path_params": scope.get("path_params") or None,
            "client_addr": client[0] if client else None,
            "authenticated_user_id": context.user.id if context.user else None,
            "key_id": context.key.id if context.key else None,
            # Set by the model-forward use cases only, once they have resolved the router.
            "router_name": context.router_name,
        }
        return {
            "method": scope["method"],
            # Without the query string: a secret passed as a URL parameter must not reach the logs.
            "path": scope["path"],
            # A field that does not apply to the route (router_name on an admin route, user on a public one) is left out.
            **{name: value for name, value in optional_fields.items() if value is not None},
        }
