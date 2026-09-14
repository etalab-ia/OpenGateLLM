import asyncio

import pytest

from api.infrastructure.fastapi._streamingresponsewithstatuscode import StreamingResponseWithStatusCode


@pytest.mark.asyncio
async def test_should_close_the_body_iterator_when_the_client_disconnects():
    # Arrange: a slow consumer, so the body iterator sits parked on its yield rather than producing
    closed = {"value": False}

    async def body():
        try:
            while True:
                yield ("data: hello\n\n", 200)
        finally:
            closed["value"] = True

    async def slow_send(message: dict) -> None:
        await asyncio.sleep(1)

    task = asyncio.create_task(StreamingResponseWithStatusCode(content=body()).stream_response(slow_send))
    await asyncio.sleep(0.05)

    # Act: the disconnect cancels the task Starlette runs stream_response in
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    # Assert: the chain is released now, not whenever the garbage collector gets to it
    assert closed["value"] is True
