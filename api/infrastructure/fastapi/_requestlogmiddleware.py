import logging
from time import perf_counter

from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
import sentry_sdk
from sentry_sdk.utils import event_from_exception
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from api.infrastructure.fastapi._requestcontext import RequestContext
from api.infrastructure.fastapi.dependencies import request_context
from api.infrastructure.fastapi.endpoints.exceptions import InternalServerHTTPException

logger = logging.getLogger("api.request")


class RequestLogMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started_at = perf_counter()
        status_code = None

        async def capture_status_and_send(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                # the row is still mutable here: the queued task only runs once the body has been sent
                if (usage_repository := request_context.get().usage_repository) is not None:
                    usage_repository.record_response_status(status_code=status_code)
            await send(message)

        try:
            await self.app(scope, receive, capture_status_and_send)
        except Exception as exception:
            request_context.get().error = type(exception).__name__
            if status_code is not None:
                raise

            self._report_to_sentry(exception)
            logger.exception("Unhandled exception while processing request", extra=self._request_fields(scope, request_context.get()))
            status_code = InternalServerHTTPException.status_code
            response = JSONResponse(status_code=status_code, content={"detail": InternalServerHTTPException.detail})
            # FastAPI attaches its BackgroundTasks to the response the handler returns, and the handler raised: carry
            # the queue over to ours, or the usage row the use case queued is dropped.
            response.background = request_context.get().background_tasks
            # through the spy, so the 500 is stamped on the row like any other answered status
            await response(scope, receive, capture_status_and_send)
        finally:
            duration_ms = round((perf_counter() - started_at) * 1000, 1)
            logger.info(
                "%s %s %s %.1fms",
                scope["method"],
                scope["path"],
                status_code,
                duration_ms,
                extra={**self._request_fields(scope, request_context.get()), "status_code": status_code, "duration_ms": duration_ms},
            )

    def _request_fields(self, scope: Scope, context: RequestContext) -> dict:
        client = scope.get("client")
        handler = scope.get("endpoint")
        optional_fields = {
            "handler": self._handler_name(handler) if handler else None,
            "path_params": scope.get("path_params") or None,
            "client_addr": client[0] if client else None,
            "authenticated_user_id": context.user.id if context.user else None,
            "key_id": context.key.id if context.key else None,
            "router_name": context.router_name,
            "error": context.error,
        }
        return {
            "method": scope["method"],
            "path": scope["path"],
            **{name: value for name, value in optional_fields.items() if value is not None},
        }

    @staticmethod
    def _report_to_sentry(exception: Exception) -> None:
        event, hint = event_from_exception(
            exception,
            client_options=sentry_sdk.get_client().options,
            mechanism={"type": "asgi", "handled": False},
        )
        sentry_sdk.capture_event(event, hint=hint)

    @staticmethod
    def _handler_name(handler: object) -> str:
        target = handler if hasattr(handler, "__qualname__") else type(handler)
        return f"{target.__module__}.{target.__qualname__}"


async def record_http_exception(request: Request, exception: HTTPException) -> Response:
    context = request_context.get()
    context.error = type(exception).__name__
    response = await http_exception_handler(request, exception)
    response.background = context.background_tasks

    return response


async def record_validation_exception(request: Request, exception: RequestValidationError) -> Response:
    context = request_context.get()
    context.error = type(exception).__name__
    response = await request_validation_exception_handler(request, exception)
    response.background = context.background_tasks

    return response
