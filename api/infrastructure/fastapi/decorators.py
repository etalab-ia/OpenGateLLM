import asyncio
from contextlib import suppress
import functools

from fastapi import Request


def cancel_on_disconnect(endpoint_func):
    @functools.wraps(endpoint_func)
    async def wrapper(*args, **kwargs):
        request: Request = kwargs["request"]
        endpoint_task = asyncio.create_task(endpoint_func(*args, **kwargs), name=f"request-{request.url.path}")
        try:
            while not endpoint_task.done():
                if await request.is_disconnected():
                    endpoint_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await endpoint_task
                    raise asyncio.CancelledError()
                await asyncio.sleep(0.1)
            return await endpoint_task
        finally:
            if not endpoint_task.done():
                endpoint_task.cancel()
                with suppress(asyncio.CancelledError):
                    await endpoint_task

    return wrapper
