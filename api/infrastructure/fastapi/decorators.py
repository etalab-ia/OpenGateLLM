import asyncio
import functools
import inspect

import anyio
from fastapi import Request, Response
from starlette.types import Receive

CLIENT_CLOSED_REQUEST = 499


def cancel_on_disconnect(endpoint):
    """Cancel the endpoint as soon as its client goes away, so the provider stops computing an answer nobody will read.

    The endpoint then answers 499 instead of raising, so that `RequestLogMiddleware` sees a status: a `CancelledError`
    would go past its `except Exception`, and the request log line and the trace would end with no status at all.
    """
    if "request" not in inspect.signature(endpoint).parameters:
        raise TypeError(f"{endpoint.__name__} needs a `request: Request` parameter to be cancelled on disconnect.")

    @functools.wraps(endpoint)
    async def cancellable_endpoint(*args, **kwargs):
        request: Request = kwargs["request"]

        with anyio.CancelScope() as endpoint_scope:
            disconnect_watcher = asyncio.create_task(_cancel_when_client_disconnects(receive=request.receive, scope=endpoint_scope))
            try:
                return await endpoint(*args, **kwargs)
            finally:
                disconnect_watcher.cancel()

        # Only reached when the watcher cancelled the scope: any other cancellation propagates through it.
        return Response(status_code=CLIENT_CLOSED_REQUEST)

    return cancellable_endpoint


async def _cancel_when_client_disconnects(receive: Receive, scope: anyio.CancelScope) -> None:
    while (await receive())["type"] != "http.disconnect":
        pass
    scope.cancel()
