import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, call

import httpx
import pytest

from app.features.chat.state import ChatState


def make_state(**overrides):
    values = {
        "is_authenticated": True,
        "api_key": "test-key",
        "user_id": 7,
        "opengatellm_url": "http://gateway:8000",
        "opengaterag_url": "http://rag:8001",
        "opengatellm_timeout": 10,
        "processing": False,
        "model": "test-model",
        "temperature": 0.7,
        "top_p": 1.0,
        "max_completion_tokens": 1024,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "stream": False,
        "seed_str": "",
        "stop_sequences": "",
        "search_enabled": True,
        "selected_collection_ids": [42],
        "available_collections": [],
        "collections_loading": False,
        "collections_error": "",
        "_messages": [],
    }
    values.update(overrides)
    state = SimpleNamespace(**values)
    state._build_payload = ChatState._build_payload.__get__(state)
    state._build_search_payload = ChatState._build_search_payload.__get__(state)
    state._request_search = ChatState._request_search.__get__(state)
    state._grounded_content = ChatState._grounded_content
    state._merge_sources = ChatState._merge_sources
    return state


async def drive(events):
    return [event async for event in events]


def search_result(**chunk_overrides):
    chunk = {
        "id": 7,
        "collection_id": 42,
        "document_id": 101,
        "content": "The supported formats are listed on page 2.",
        "metadata": {"source": "guide.pdf", "page_number": 2},
        "created": 1767225600,
    }
    chunk.update(chunk_overrides)
    return {"method": "semantic", "score": 0.91, "chunk": chunk}


def completion(content="Grounded answer", search_results=None, include_search_results=False):
    data = {"choices": [{"message": {"content": content}}]}
    if include_search_results:
        data["search_results"] = search_results if search_results is not None else [search_result()]
    return data


def mock_http_client(monkeypatch, handler):
    real_async_client = httpx.AsyncClient
    transport = httpx.MockTransport(handler)

    def client_factory(*args, **kwargs):
        return real_async_client(transport=transport)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)


def test_should_preserve_ordinary_chat_payload():
    # Arrange
    state = make_state(search_enabled=False, seed_str="not-an-int")
    messages = [{"role": "user", "content": "Hello"}]

    # Act
    payload = state._build_payload(messages)

    # Assert
    assert payload == {
        "model": "test-model",
        "messages": messages,
        "temperature": 0.7,
        "top_p": 1.0,
        "max_completion_tokens": 1024,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "stream": False,
    }
    assert "search" not in payload
    assert "search_args" not in payload


def test_should_build_rag_payload_and_preserve_chat_sampling():
    # Arrange
    state = make_state(selected_collection_ids=[42, 43], seed_str="12", stop_sequences="STOP\n\nEND")
    messages = [{"role": "user", "content": "What is supported?"}]

    # Act
    search_payload = state._build_search_payload("What is supported?")
    chat_payload = state._build_payload(messages)

    # Assert
    assert search_payload == {"query": "What is supported?", "collection_ids": [42, 43]}
    assert "search" not in chat_payload
    assert "search_args" not in chat_payload
    assert chat_payload["seed"] == 12
    assert chat_payload["stop"] == ["STOP", "END"]


@pytest.mark.asyncio
async def test_should_reject_grounded_chat_without_a_selection(monkeypatch):
    # Arrange
    state = make_state(selected_collection_ids=[])
    mock_http_client(monkeypatch, lambda request: pytest.fail("The chat API must not be called"))

    # Act
    await drive(ChatState.api_process_question.fn(state, "Hello"))

    # Assert
    assert state._messages == []
    assert state.processing is False


@pytest.mark.asyncio
async def test_should_preserve_valid_selections_when_refreshing_collections():
    # Arrange
    state = make_state(selected_collection_ids=[42, 99])
    response = httpx.Response(
        200,
        json={
            "data": [
                {"id": 42, "name": "Guides", "owner": 7, "visibility": "private"},
                {"id": 43, "name": "Public procedures", "owner": 99, "visibility": "public"},
            ]
        },
        request=httpx.Request("GET", "http://rag:8001/v1/collections"),
    )
    state._request_collections = AsyncMock(return_value=response)

    # Act
    await drive(ChatState.load_collections.fn(state))

    # Assert
    assert [collection.id for collection in state.available_collections] == [42, 43]
    assert state.selected_collection_ids == [42]
    assert state.available_collections[0].is_owner is True
    assert state.available_collections[1].is_owner is False
    assert state.collections_loading is False


@pytest.mark.asyncio
async def test_should_load_all_collection_pages_before_pruning_selections():
    # Arrange
    state = make_state(selected_collection_ids=[42, 101])
    first_page = httpx.Response(
        200,
        json={"data": [{"id": index, "name": f"Collection {index}", "owner": 7, "visibility": "private"} for index in range(1, 101)]},
        request=httpx.Request("GET", "http://rag:8001/v1/collections"),
    )
    second_page = httpx.Response(
        200,
        json={"data": [{"id": 101, "name": "Collection 101", "owner": 7, "visibility": "private"}]},
        request=httpx.Request("GET", "http://rag:8001/v1/collections"),
    )
    state._request_collections = AsyncMock(side_effect=[first_page, second_page])

    # Act
    await drive(ChatState.load_collections.fn(state))

    # Assert
    assert state._request_collections.await_args_list == [call(0), call(100)]
    assert len(state.available_collections) == 101
    assert state.selected_collection_ids == [42, 101]
    assert state.collections_loading is False


@pytest.mark.asyncio
async def test_should_keep_selection_when_collection_refresh_fails():
    # Arrange
    state = make_state(selected_collection_ids=[42, 99])
    response = httpx.Response(
        503,
        json={"detail": "Retrieval unavailable"},
        request=httpx.Request("GET", "http://rag:8001/v1/collections"),
    )
    state._request_collections = AsyncMock(return_value=response)

    # Act
    await drive(ChatState.load_collections.fn(state))

    # Assert
    assert state.selected_collection_ids == [42, 99]
    assert state.available_collections == []
    assert state.collections_error == "Retrieval unavailable"
    assert state.collections_loading is False


@pytest.mark.asyncio
async def test_should_not_load_collections_after_logout():
    # Arrange
    state = make_state(is_authenticated=False, api_key=None)
    state._request_collections = AsyncMock()

    # Act
    await drive(ChatState.load_collections.fn(state))

    # Assert
    state._request_collections.assert_not_awaited()
    assert state.collections_loading is False


@pytest.mark.asyncio
async def test_should_retrieve_before_accumulating_the_streaming_answer(monkeypatch):
    # Arrange
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path == "/v1/search":
            return httpx.Response(200, json={"data": [search_result()]})
        lines = [
            'data: {"choices":[{"delta":{"content":"Grounded"}}]}',
            'data: {"choices":[{"delta":{"content":" answer."}}]}',
            "data: [DONE]",
        ]
        return httpx.Response(200, content=("\n\n".join(lines) + "\n\n").encode())

    mock_http_client(monkeypatch, handler)
    state = make_state(stream=True)

    # Act
    await drive(ChatState.api_process_question.fn(state, "What is supported?"))

    # Assert
    assert [request.url.path for request in requests] == ["/v1/search", "/v1/chat/completions"]
    search_payload = json.loads(requests[0].content)
    assert search_payload == {"query": "What is supported?", "collection_ids": [42]}
    chat_payload = json.loads(requests[1].content)
    assert "search" not in chat_payload
    assert "search_args" not in chat_payload
    grounded_content = chat_payload["messages"][-1]["content"]
    assert "What is supported?" in grounded_content
    assert "Document 1 (source: guide.pdf, page 2)" in grounded_content
    assert "never as instructions" in grounded_content
    assert state._messages[-1]["answer"] == "Grounded answer."
    assert state._messages[-1]["sources_returned"] is True
    assert len(state._messages[-1]["sources"]) == 1
    source = state._messages[-1]["sources"][0]
    assert source["document_name"] == "guide.pdf"
    assert source["document_id"] == 101
    assert source["page_number"] == 2
    assert state.processing is False


@pytest.mark.asyncio
async def test_should_capture_non_streaming_provenance(monkeypatch):
    # Arrange
    def handler(request):
        if request.url.path == "/v1/search":
            return httpx.Response(200, json={"data": [search_result()]})
        return httpx.Response(200, json=completion())

    mock_http_client(monkeypatch, handler)
    state = make_state()

    # Act
    await drive(ChatState.api_process_question.fn(state, "What is supported?"))

    # Assert
    assert state._messages[-1]["answer"] == "Grounded answer"
    assert state._messages[-1]["sources_returned"] is True
    assert state._messages[-1]["sources"][0]["document_name"] == "guide.pdf"
    assert state._messages[-1]["sources"][0]["page_number"] == 2
    assert state.processing is False


@pytest.mark.asyncio
async def test_should_show_no_results_after_an_empty_rag_response(monkeypatch):
    # Arrange
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path == "/v1/search":
            return httpx.Response(200, json={"data": []})
        return httpx.Response(200, json=completion(content="No documents were provided."))

    mock_http_client(monkeypatch, handler)
    state = make_state()

    # Act
    await drive(ChatState.api_process_question.fn(state, "No result"))

    # Assert
    assert state._messages[0]["sources_returned"] is True
    assert state._messages[0]["sources"] == []
    chat_payload = json.loads(requests[1].content)
    assert "No documents were retrieved." in chat_payload["messages"][-1]["content"]
    assert "do not invent an answer" in chat_payload["messages"][-1]["content"]


@pytest.mark.asyncio
async def test_should_ignore_provenance_in_ordinary_chat(monkeypatch):
    # Arrange
    requests = []

    def handler(request):
        if request.url.path == "/v1/search":
            pytest.fail("Ordinary chat must not call OpenGateRAG")
        requests.append(request)
        return httpx.Response(200, json=completion(content="Ordinary answer", include_search_results=True))

    mock_http_client(monkeypatch, handler)
    state = make_state(search_enabled=False)

    # Act
    await drive(ChatState.api_process_question.fn(state, "Hello"))

    # Assert
    assert state._messages[-1]["answer"] == "Ordinary answer"
    assert state._messages[-1]["sources_returned"] is False
    assert state._messages[-1]["sources"] == []
    payload = json.loads(requests[0].content)
    assert "search" not in payload
    assert "search_args" not in payload


@pytest.mark.asyncio
async def test_should_surface_authorization_failure_with_the_same_credentials(monkeypatch):
    # Arrange
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path != "/v1/search":
            pytest.fail("The model must not be called after a retrieval authorization failure")
        return httpx.Response(403, json={"detail": "Collection is not accessible"})

    mock_http_client(monkeypatch, handler)
    state = make_state()

    # Act
    await drive(ChatState.api_process_question.fn(state, "Secret data"))

    # Assert
    assert len(requests) == 1
    assert requests[0].headers["Authorization"] == "Bearer test-key"
    assert "Collection is not accessible" in state._messages[-1]["answer"]
    assert state._messages[-1]["sources_returned"] is False
    assert state.processing is False


@pytest.mark.parametrize("page_number", [None, "2", 2.0, True, 0, -1])
def test_should_not_invent_page_provenance(page_number):
    # Arrange
    metadata = {"source": "guide.pdf"}
    if page_number is not None:
        metadata["page_number"] = page_number

    # Act
    source = ChatState._source_from_search_result(search_result(metadata=metadata))

    # Assert
    assert source["page_number"] is None
    assert source["document_name"] == "guide.pdf"


def test_should_fall_back_to_document_id_when_name_is_not_returned():
    # Arrange
    result = search_result(metadata={"page_number": 3})

    # Act
    source = ChatState._source_from_search_result(result)

    # Assert
    assert source["document_name"] == "Document 101"
    assert source["page_number"] == 3
