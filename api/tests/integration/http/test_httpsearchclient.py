import json

import httpx
import pytest
import respx

from api.domain.search.entities import SearchArgs, Searches
from api.domain.search.errors import SearchStatusCodeError, SearchUnreachableError
from api.infrastructure.http import HttpSearchClient

SEARCH_SERVICE_URL = "http://opengaterag:8000"
SEARCH_URL = f"{SEARCH_SERVICE_URL}/v1/search"
KEY_VALUE = "sk-search-key"


def _search_payload(content: str = "Paris is the capital of France.") -> dict:
    return {
        "object": "list",
        "data": [
            {
                "method": "semantic",
                "score": 0.92,
                "chunk": {"object": "chunk", "id": 1, "collection_id": 2, "document_id": 3, "content": content},
            }
        ],
    }


@pytest.fixture
def search_client() -> HttpSearchClient:
    return HttpSearchClient(url=SEARCH_SERVICE_URL)


@pytest.mark.asyncio(loop_scope="session")
class TestHttpSearchClient:
    @respx.mock
    async def test_should_return_searches_when_the_service_answers(self, search_client: HttpSearchClient):
        respx.post(url=SEARCH_URL).mock(return_value=httpx.Response(status_code=200, json=_search_payload()))

        result = await search_client.search(key_value=KEY_VALUE, query="capital of France?", args=SearchArgs(limit=5))

        assert isinstance(result, Searches)
        assert result.data[0].chunk.content == "Paris is the capital of France."
        assert respx.calls.last.request.headers["authorization"] == f"Bearer {KEY_VALUE}"

    @respx.mock
    async def test_should_send_the_query_alongside_the_search_arguments(self, search_client: HttpSearchClient):
        route = respx.post(url=SEARCH_URL).mock(return_value=httpx.Response(status_code=200, json=_search_payload()))

        await search_client.search(key_value=KEY_VALUE, query="capital of France?", args=SearchArgs(limit=5, collection_ids=[7]))

        body = json.loads(route.calls.last.request.read())
        assert body["query"] == "capital of France?"
        assert body["limit"] == 5
        assert body["collection_ids"] == [7]

    @respx.mock
    async def test_should_return_status_code_error_when_the_service_rejects_the_request(self, search_client: HttpSearchClient):
        respx.post(url=SEARCH_URL).mock(return_value=httpx.Response(status_code=403, json={"detail": "Forbidden"}))

        result = await search_client.search(key_value=KEY_VALUE, query="q", args=SearchArgs())

        assert result == SearchStatusCodeError(status_code=403, detail="Forbidden")

    @respx.mock
    async def test_should_fall_back_to_the_raw_body_when_the_error_is_not_json(self, search_client: HttpSearchClient):
        respx.post(url=SEARCH_URL).mock(return_value=httpx.Response(status_code=502, text="bad gateway"))

        result = await search_client.search(key_value=KEY_VALUE, query="q", args=SearchArgs())

        assert result == SearchStatusCodeError(status_code=502, detail="bad gateway")

    @respx.mock
    async def test_should_return_unreachable_error_when_the_service_is_down(self, search_client: HttpSearchClient):
        respx.post(url=SEARCH_URL).mock(side_effect=httpx.ConnectError("connection refused"))

        result = await search_client.search(key_value=KEY_VALUE, query="q", args=SearchArgs())

        assert isinstance(result, SearchUnreachableError)

    @respx.mock
    async def test_should_return_unreachable_error_when_the_payload_does_not_match_the_contract(self, search_client: HttpSearchClient):
        respx.post(url=SEARCH_URL).mock(return_value=httpx.Response(status_code=200, json={"data": [{"unexpected": True}]}))

        result = await search_client.search(key_value=KEY_VALUE, query="q", args=SearchArgs())

        assert isinstance(result, SearchUnreachableError)
