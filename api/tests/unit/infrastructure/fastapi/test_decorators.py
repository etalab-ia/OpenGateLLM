import asyncio
from types import SimpleNamespace

from fastapi import HTTPException
import pytest

from api.infrastructure.fastapi.decorators import CLIENT_CLOSED_REQUEST, cancel_on_disconnect


def mock_request_from_client_waiting_for_response():
    async def receive() -> dict:
        await asyncio.Event().wait()

    return SimpleNamespace(receive=receive)


def mock_request_from_client_that_disconnects_after(event: asyncio.Event):
    async def receive() -> dict:
        await event.wait()
        return {"type": "http.disconnect"}

    return SimpleNamespace(receive=receive)


class TestCancelOnDisconnect:
    @pytest.mark.asyncio
    async def test_should_return_the_endpoint_response_while_the_client_is_connected(self):
        # Arrange
        @cancel_on_disconnect
        async def endpoint(request):
            return "response"

        # Act
        result = await endpoint(request=mock_request_from_client_waiting_for_response())

        # Assert
        assert result == "response"

    @pytest.mark.asyncio
    async def test_should_cancel_the_endpoint_and_answer_499_when_the_client_disconnects(self):
        # Arrange
        endpoint_has_started_processing_request = asyncio.Event()
        endpoint_processing_was_cancelled = False

        @cancel_on_disconnect
        async def endpoint(request):
            nonlocal endpoint_processing_was_cancelled
            endpoint_has_started_processing_request.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                endpoint_processing_was_cancelled = True
                raise

        # Act
        result = await endpoint(request=mock_request_from_client_that_disconnects_after(endpoint_has_started_processing_request))

        # Assert
        assert endpoint_processing_was_cancelled is True
        assert result.status_code == CLIENT_CLOSED_REQUEST

    @pytest.mark.asyncio
    async def test_should_let_the_endpoint_exceptions_through(self):
        # Arrange
        @cancel_on_disconnect
        async def endpoint(request):
            raise HTTPException(status_code=404)

        # Act
        with pytest.raises(HTTPException) as raised:
            await endpoint(request=mock_request_from_client_waiting_for_response())

        # Assert
        assert raised.value.status_code == 404

    @pytest.mark.asyncio
    async def test_should_propagate_a_cancellation_that_does_not_come_from_the_client(self):
        # Arrange
        endpoint_has_started_processing_request = asyncio.Event()

        @cancel_on_disconnect
        async def endpoint(request):
            endpoint_has_started_processing_request.set()
            await asyncio.Event().wait()

        endpoint_task = asyncio.create_task(endpoint(request=mock_request_from_client_waiting_for_response()))
        await endpoint_has_started_processing_request.wait()

        # Act
        endpoint_task.cancel()

        # Assert
        with pytest.raises(asyncio.CancelledError):
            await endpoint_task

    def test_should_reject_an_endpoint_without_request_parameter(self):
        # Arrange
        async def endpoint(body):
            return body

        # Act / Assert
        with pytest.raises(TypeError):
            cancel_on_disconnect(endpoint)
