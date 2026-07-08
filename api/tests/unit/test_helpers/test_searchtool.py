from datetime import datetime
from http import HTTPMethod
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
import pytest

from api.helpers._searchtool import Chunk, ComparisonFilter, CompoundFilter, Search, SearchArgs, SearchMethod, SearchTool
from api.schemas.core.models import RequestContent
from api.utils.exceptions import WrongSearchMethodException
from api.utils.variables import EndpointRoute


class FakeResponse:
    def __init__(self, payload, raise_for_status_side_effect=None):
        self.payload = payload
        self.raise_for_status_side_effect = raise_for_status_side_effect

    def raise_for_status(self):
        if self.raise_for_status_side_effect:
            raise self.raise_for_status_side_effect

    def json(self):
        return self.payload


class FakeAsyncClient:
    def __init__(self, response):
        self.response = response
        self.post = AsyncMock(return_value=response)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


def build_request_content(body: dict) -> RequestContent:
    return RequestContent(method=HTTPMethod.POST, endpoint=EndpointRoute.CHAT_COMPLETIONS, body=body)


def test_chunk_normalizes_legacy_metadata():
    chunk = Chunk(
        id=1,
        collection_id=2,
        document_id=3,
        content="Chunk content",
        metadata={"tags": ["foo", " ", "bar"], "empty": None, "page": 4},
        created=datetime.fromtimestamp(1_700_000_000),
    )

    assert chunk.metadata == {"tags": "foo,bar", "page": 4}
    assert chunk.model_dump(mode="json")["created"] == 1_700_000_000


def test_search_args_rejects_score_threshold_with_non_semantic_method():
    with pytest.raises(WrongSearchMethodException) as exc_info:
        SearchArgs(method=SearchMethod.LEXICAL, score_threshold=0.5)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Score threshold is only available for semantic search method"


def test_compound_filter_accepts_multiple_comparison_filters():
    search_args = SearchArgs(
        metadata_filters={
            "operator": "and",
            "filters": [
                {"key": "source", "type": "eq", "value": "faq"},
                {"key": "title", "type": "co", "value": "OpenGate"},
            ],
        }
    )

    assert isinstance(search_args.metadata_filters, CompoundFilter)
    assert all(isinstance(filter_, ComparisonFilter) for filter_ in search_args.metadata_filters.filters)


@pytest.mark.asyncio
async def test_search_tool_returns_original_request_when_tools_are_absent():
    request_content = build_request_content(body={"messages": [{"role": "user", "content": "Question"}]})
    search_tool = SearchTool(opengaterag_url="https://rag.example", postgres_session=AsyncMock(), user_id=42)

    result = await search_tool.call(request_content)

    assert result is request_content
    assert result.body == {"messages": [{"role": "user", "content": "Question"}]}


@pytest.mark.asyncio
async def test_search_tool_raises_422_for_invalid_search_tool_payload():
    request_content = build_request_content(
        body={
            "tools": [{"type": "search", "limit": 0}],
            "messages": [{"role": "user", "content": "Question"}],
        }
    )
    search_tool = SearchTool(opengaterag_url="https://rag.example", postgres_session=AsyncMock(), user_id=42)

    with pytest.raises(HTTPException) as exc_info:
        await search_tool.call(request_content)

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail[0]["loc"] == ["limit"]


@pytest.mark.asyncio
async def test_search_tool_calls_rag_and_rewrites_last_message():
    request_content = build_request_content(
        body={
            "tools": [{"type": "function", "name": "other"}, {"type": "search", "collection_ids": [12], "method": "semantic", "limit": 3}],
            "messages": [{"role": "system", "content": "Be concise"}, {"role": "user", "content": "What is OpenGateLLM?"}],
        }
    )
    search_result = Search(
        method=SearchMethod.SEMANTIC,
        score=0.92,
        chunk=Chunk(id=1, collection_id=12, document_id=5, content="OpenGateLLM is an API gateway.", metadata={"source": "docs"}),
    )
    fake_client = FakeAsyncClient(response=FakeResponse(payload=[search_result]))
    search_tool = SearchTool(opengaterag_url="https://rag.example", postgres_session=AsyncMock(), user_id=42)
    search_tool._upsert_key = AsyncMock(return_value=SimpleNamespace(value="search-token"))

    with patch("api.helpers._searchtool.httpx.AsyncClient", return_value=fake_client):
        result = await search_tool.call(request_content)

    search_tool._upsert_key.assert_awaited_once()
    fake_client.post.assert_awaited_once_with(
        url="https://rag.example/search",
        headers={"Authorization": "Bearer search-token"},
        json={
            "query": "What is OpenGateLLM?",
            "collection_ids": [12],
            "document_ids": [],
            "metadata_filters": None,
            "limit": 3,
            "offset": 0,
            "method": SearchMethod.SEMANTIC,
            "rff_k": 60,
            "score_threshold": 0.0,
        },
    )
    assert result.body["tools"] == [{"type": "function", "name": "other"}]
    assert "User query: What is OpenGateLLM?" in result.body["messages"][-1]["content"]
    assert "OpenGateLLM is an API gateway." in result.body["messages"][-1]["content"]
    assert result.additional_data["search_results"] == [search_result.model_dump(mode="json")]


@pytest.mark.asyncio
async def test_search_tool_returns_original_request_when_rag_call_fails():
    request_content = build_request_content(
        body={
            "tools": [{"type": "search"}],
            "messages": [{"role": "user", "content": "Question"}],
        }
    )
    fake_client = FakeAsyncClient(response=FakeResponse(payload=[], raise_for_status_side_effect=HTTPException(status_code=503)))
    search_tool = SearchTool(opengaterag_url="https://rag.example", postgres_session=AsyncMock(), user_id=42)
    search_tool._upsert_key = AsyncMock(return_value=SimpleNamespace(value="search-token"))

    with patch("api.helpers._searchtool.httpx.AsyncClient", return_value=fake_client):
        result = await search_tool.call(request_content)

    assert result is request_content
    assert result.body["messages"][-1]["content"] == "Question"
    assert result.additional_data == {}
