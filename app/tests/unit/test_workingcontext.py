import pytest
import asyncio

from app.helpers.models._workingcontext import WorkingContext


class DummyClient:
    def __init__(self, name="dummy"):
        self.name = name


@pytest.mark.asyncio
async def test_init_sets_fields():
    def handler(c):
        return "ok"

    ctx = WorkingContext("test-endpoint", handler)

    assert ctx.endpoint == "test-endpoint"
    assert ctx.handler == handler
    assert isinstance(ctx.id, str)
    assert isinstance(ctx.result, asyncio.Future)
    assert ctx.loop is asyncio.get_running_loop()


@pytest.mark.asyncio
async def test_work_with_sync_handler():
    def handler(client):
        return f"hello {client.name}"

    ctx = WorkingContext("ep", handler)
    client = DummyClient("world")

    result = await ctx.work(client)
    assert result == "hello world"


@pytest.mark.asyncio
async def test_work_with_async_handler():
    async def handler(client):
        await asyncio.sleep(0.01)
        return f"async {client.name}"

    ctx = WorkingContext("ep", handler)
    client = DummyClient("world")

    result = await ctx.work(client)
    assert result == "async world"


@pytest.mark.asyncio
async def test_work_returns_exception_on_error():
    def handler(client):
        raise ValueError("boom")

    ctx = WorkingContext("ep", handler)
    client = DummyClient()

    result = await ctx.work(client)
    assert isinstance(result, ValueError)
    assert str(result) == "boom"


@pytest.mark.asyncio
async def test_send_result_sets_result():
    def handler(c):
        return "unused"

    ctx = WorkingContext("ep", handler)
    ctx.send_result("ok")

    result = await ctx.result
    assert result == "ok"


@pytest.mark.asyncio
async def test_send_result_sets_exception():
    def handler(c):
        return "unused"

    ctx = WorkingContext("ep", handler)
    exc = RuntimeError("fail")
    ctx.send_result(exc)

    with pytest.raises(RuntimeError, match="fail"):
        await ctx.result
