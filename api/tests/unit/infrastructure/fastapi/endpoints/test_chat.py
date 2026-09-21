from collections.abc import AsyncGenerator

import pytest

from api.domain.provider.entities import ProviderChunkResponse
from api.infrastructure.fastapi.endpoints.chat import _as_stream_chunks


async def _stream(*chunks: ProviderChunkResponse) -> AsyncGenerator[ProviderChunkResponse]:
    for chunk in chunks:
        yield chunk


async def _collect(chunks) -> list:
    return [chunk async for chunk in chunks]


class TestAsStreamChunks:
    @pytest.mark.asyncio
    async def test_should_frame_each_line_as_a_server_sent_event(self):
        # Arrange
        chunks = _stream(
            ProviderChunkResponse(content='data: {"id": "chat-1"}', status_code=200),
            ProviderChunkResponse(content="data: [DONE]", status_code=200),
        )

        # Act
        collected = await _collect(_as_stream_chunks(chunks))

        # Assert
        assert collected == [('data: {"id": "chat-1"}\n\n', 200), ("data: [DONE]\n\n", 200)]

    @pytest.mark.asyncio
    async def test_should_leave_an_error_chunk_unframed_when_it_arrives_first(self):
        # Arrange
        chunks = _stream(ProviderChunkResponse(content='{"detail": "Model is too busy"}', status_code=503))

        # Act
        collected = await _collect(_as_stream_chunks(chunks))

        # Assert
        assert collected == [('{"detail": "Model is too busy"}', 503)], (
            "the status line is still open, so this chunk is the response body: framing it would corrupt what the client parses"
        )

    @pytest.mark.asyncio
    async def test_should_announce_an_error_as_an_event_when_it_arrives_mid_stream(self):
        # Arrange
        chunks = _stream(
            ProviderChunkResponse(content='data: {"id": "chat-1"}', status_code=200),
            ProviderChunkResponse(content='{"detail": "Model is too busy"}', status_code=503),
        )

        # Act
        collected = await _collect(_as_stream_chunks(chunks))

        # Assert
        assert collected == [
            ('data: {"id": "chat-1"}\n\n', 200),
            ('event: error\ndata: {"detail": "Model is too busy"}\n\n', 503),
        ], "the client is already reading an event stream, so a late failure has to reach it as an event"

    @pytest.mark.asyncio
    async def test_should_stop_after_an_error_that_arrives_first(self):
        # Arrange
        chunks = _stream(
            ProviderChunkResponse(content='{"detail": "Model is too busy"}', status_code=503),
            ProviderChunkResponse(content="data: [DONE]", status_code=200),
        )

        # Act
        collected = await _collect(_as_stream_chunks(chunks))

        # Assert
        assert collected == [('{"detail": "Model is too busy"}', 503)]

    @pytest.mark.asyncio
    async def test_should_close_the_use_case_stream_when_the_client_stops_reading(self):
        # Arrange: a provider that never stops, so the use case generator is parked on a yield when the client leaves
        use_case_reached_its_finally = False

        async def use_case_stream() -> AsyncGenerator[ProviderChunkResponse]:
            nonlocal use_case_reached_its_finally
            try:
                while True:
                    yield ProviderChunkResponse(content='data: {"id": "chat-1"}', status_code=200)
            finally:
                use_case_reached_its_finally = True  # where the use case bills the tokens it already delivered

        stream = use_case_stream()  # the local reference is the point: no garbage collection can do this for us
        adapter = _as_stream_chunks(stream)

        # Act: the client reads one event, then disconnects
        await adapter.__anext__()
        await adapter.aclose()

        # Assert
        assert use_case_reached_its_finally, (
            "closing the adapter must close the stream it consumes: `async for` does not, so without `aclosing` the use "
            "case stays parked on its yield and the usage row is written with no tokens"
        )
