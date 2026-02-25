import json
from time import sleep
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from api.schemas.chat import ChatCompletion, ChatCompletionChunk
from api.schemas.models import ModelType
from api.utils.variables import EndpointRoute


@pytest.fixture(scope="module")
def model_id(client: TestClient):
    response = client.get_without_permissions(url=f"/v1{EndpointRoute.MODELS}")
    assert response.status_code == 200, response.text
    response_json = response.json()

    model = [model for model in response_json["data"] if model["type"] == ModelType.TEXT_GENERATION][0]
    model_id = model["id"]

    yield model_id


@pytest.fixture(scope="function")
def collection_id(client: TestClient):
    # Create a collection
    response = client.post_without_permissions(url=f"/v1{EndpointRoute.COLLECTIONS}", json={"name": f"test_collection_{uuid4()}"})
    assert response.status_code == 201, response.text
    collection_id = response.json()["id"]

    yield collection_id

    # delete the collection
    response = client.delete_without_permissions(url=f"/v1{EndpointRoute.COLLECTIONS}/{collection_id}")
    assert response.status_code == 204, response.text


@pytest.fixture(scope="function")
def document_id(client: TestClient, collection_id: int):
    # create a document
    data = {"collection_id": collection_id, "name": "test_search_document.pdf"}
    response = client.post_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}", data=data)
    assert response.status_code == 201, response.text
    document_id = response.json()["id"]

    yield document_id

    # delete the document
    response = client.delete_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}/{document_id}")
    assert response.status_code == 204, response.text


@pytest.fixture(scope="function")
def chunks_ids(client: TestClient, document_id: int):
    data = {
        "chunks": [
            {"content": "Qui est Albert ?", "metadata": {"source_title": "test", "source_page": "1"}},
            {"content": "Qui est Erasmus ?", "metadata": {"source_title": "test", "source_page": "2"}},
            {"content": "Qui est Voltaire ?", "metadata": {"source_title": "test", "source_page": "3"}},
        ]
    }
    response = client.post_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}/{document_id}/chunks", json=data)
    assert response.status_code == 201, response.text
    chunk_ids = response.json()["ids"]
    sleep(2)

    yield chunk_ids


@pytest.mark.usefixtures("client", "model_id", "collection_id", "document_id", "chunks_ids")
class TestTools:
    @staticmethod
    def _post_chat_with_search_tool(client: TestClient, model_id: str, query: str, tool_args: dict | None = None, stream: bool = False):
        tool = {"type": "search"}
        if tool_args:
            tool.update(tool_args)

        body = {
            "model": model_id,
            "messages": [{"role": "user", "content": query}],
            "stream": stream,
            "n": 1,
            "max_completion_tokens": 10,
            "tools": [tool],
        }
        return client.post_without_permissions(url=f"/v1{EndpointRoute.CHAT_COMPLETIONS}", json=body)

    @staticmethod
    def _create_document_with_chunk(client: TestClient, collection_id: int, chunks: list[dict] = []) -> int:
        response = client.post_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}", data={"collection_id": collection_id, "name": "test.pdf"})
        assert response.status_code == 201, response.text
        document_id = response.json()["id"]

        if chunks:
            response = client.post_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}/{document_id}/chunks", json={"chunks": chunks})
            assert response.status_code == 201, response.text
            sleep(1)

        return document_id

    def test_tools_search_unstreamed_response(self, client: TestClient, model_id: str, document_id: int):
        """Test the GET /chat/completions search unstreamed response."""

        response = self._post_chat_with_search_tool(client=client, model_id=model_id, query="Qui est Albert ?")
        assert response.status_code == 200, response.text
        ChatCompletion(**response.json())  # test output format
        assert response.json()["search_results"][0]["chunk"]["document_id"] == document_id

    def test_tools_search_streamed_response(self, client: TestClient, model_id: str, document_id: int, collection_id: int):
        """Test the GET /chat/completions search streamed response."""
        response = self._post_chat_with_search_tool(client=client, model_id=model_id, query="Qui est Albert ?", stream=True)
        assert response.status_code == 200, response.text

        i = 0
        chunks = list()
        for line in response.iter_lines():
            if line:
                line = line.lstrip("data: ")
                if line != "[DONE]":
                    chunk = json.loads(line)
                    chunk = ChatCompletionChunk(**chunk)
                    chunks.append(chunk)
                    continue
                # check that the last chunk has a search result
                assert chunks[i - 1].search_results[0].chunk.document_id == document_id
                break

    def test_tools_search_with_pagination_limit(self, client: TestClient, model_id: str, document_id: int, chunks_ids: list[int]):
        """Test search tool with pagination limit."""

        response = self._post_chat_with_search_tool(
            client=client,
            model_id=model_id,
            query="Qui est Albert ?",
            tool_args={"limit": 2},
        )

        assert response.status_code == 200, response.text
        chat_completion = ChatCompletion(**response.json())
        assert len(chat_completion.search_results) == 2
        assert all(search.chunk.id in chunks_ids for search in chat_completion.search_results)
        assert chat_completion.search_results[0].chunk.document_id == document_id

    def test_tools_search_with_pagination_offset(self, client: TestClient, model_id: str):
        """Test search tool with pagination offset."""

        response = self._post_chat_with_search_tool(
            client=client,
            model_id=model_id,
            query="Qui est Albert ?",
            tool_args={"limit": 2, "offset": 0},
        )
        assert response.status_code == 200, response.text
        chat_completion = ChatCompletion(**response.json())
        assert len(chat_completion.search_results) == 2
        first_chunk_id = chat_completion.search_results[0].chunk.id
        second_chunk_id = chat_completion.search_results[1].chunk.id

        response = self._post_chat_with_search_tool(
            client=client,
            model_id=model_id,
            query="Qui est Albert ?",
            tool_args={"limit": 2, "offset": 1},
        )
        assert response.status_code == 200, response.text
        chat_completion = ChatCompletion(**response.json())
        assert len(chat_completion.search_results) == 1  # only one chunk left
        assert chat_completion.search_results[0].chunk.id == second_chunk_id
        assert first_chunk_id not in [search.chunk.id for search in chat_completion.search_results]

    def test_tools_search_with_query_from_last_message(self, client: TestClient, model_id: str):
        """Test search tool uses the last user message as query."""

        response = self._post_chat_with_search_tool(
            client=client,
            model_id=model_id,
            query="Voltaire",
            tool_args={"limit": 1},
        )
        assert response.status_code == 200, response.text
        chat_completion = ChatCompletion(**response.json())
        assert len(chat_completion.search_results) == 1
        assert chat_completion.search_results[0].chunk.content == "Qui est Voltaire ?"

    def test_tools_search_with_score_threshold(self, client: TestClient, model_id: str):
        """Test search tool with a score threshold."""

        response = self._post_chat_with_search_tool(
            client=client,
            model_id=model_id,
            query="Voltaire",
            tool_args={"limit": 3},
        )
        assert response.status_code == 200, response.text
        chat_completion = ChatCompletion(**response.json())
        first_chunk_id = chat_completion.search_results[0].chunk.id

        first_score = chat_completion.search_results[0].score
        second_score = chat_completion.search_results[1].score
        third_score = chat_completion.search_results[2].score
        assert first_score >= second_score >= third_score

        response = self._post_chat_with_search_tool(
            client=client,
            model_id=model_id,
            query="Voltaire",
            tool_args={"limit": 3, "score_threshold": first_score},
        )
        assert response.status_code == 200, response.text
        chat_completion = ChatCompletion(**response.json())
        assert len(chat_completion.search_results) == 1
        assert chat_completion.search_results[0].chunk.id == first_chunk_id

    def test_tools_search_with_invalid_collection(self, client: TestClient, model_id: str):
        """Test search tool with an invalid collection."""
        response = self._post_chat_with_search_tool(
            client=client,
            model_id=model_id,
            query="Erasmus",
            tool_args={"collection_ids": [100], "limit": 3},
        )
        assert response.status_code == 404, response.text

    def test_tools_search_with_empty_query(self, client: TestClient, model_id: str):
        """Test search tool with an empty user query."""
        response = self._post_chat_with_search_tool(client=client, model_id=model_id, query="", tool_args={"limit": 3})
        assert response.status_code == 200, response.text
        chat_completion = ChatCompletion(**response.json())
        assert len(chat_completion.search_results) == 0

    def test_tools_search_with_collection_ids_filter(self, collection_id: int, client: TestClient, model_id: str):
        # create a collection, document and chunks
        response = client.post_without_permissions(url=f"/v1{EndpointRoute.COLLECTIONS}", json={"name": f"test_collection_{uuid4()}"})
        assert response.status_code == 201, response.text
        second_collection_id = response.json()["id"]

        self._create_document_with_chunk(client=client, collection_id=second_collection_id, chunks=[{"content": "Test"}])

        response = self._post_chat_with_search_tool(client=client, model_id=model_id, query="Test", tool_args={"limit": 10})
        assert response.status_code == 200, response.text
        chat_completion = ChatCompletion(**response.json())
        assert collection_id in [search.chunk.collection_id for search in chat_completion.search_results]
        assert second_collection_id in [search.chunk.collection_id for search in chat_completion.search_results]

        response = self._post_chat_with_search_tool(
            client=client,
            model_id=model_id,
            query="Test",
            tool_args={"collection_ids": [collection_id], "limit": 10},
        )
        assert response.status_code == 200, response.text
        chat_completion = ChatCompletion(**response.json())
        assert collection_id in [search.chunk.collection_id for search in chat_completion.search_results]
        assert second_collection_id not in [search.chunk.collection_id for search in chat_completion.search_results]

        # legacy alias: collections
        response = self._post_chat_with_search_tool(
            client=client,
            model_id=model_id,
            query="Test",
            tool_args={"collections": [collection_id], "limit": 10},
        )
        assert response.status_code == 200, response.text
        chat_completion = ChatCompletion(**response.json())
        assert collection_id in [search.chunk.collection_id for search in chat_completion.search_results]
        assert second_collection_id not in [search.chunk.collection_id for search in chat_completion.search_results]

    def test_tools_search_with_document_ids_filter(self, client: TestClient, model_id: str, collection_id: int, document_id: int):
        # create a document and chunks
        second_document_id = self._create_document_with_chunk(client=client, collection_id=collection_id, chunks=[{"content": "Test"}])

        response = self._post_chat_with_search_tool(
            client=client,
            model_id=model_id,
            query="Test",
            tool_args={"document_ids": [document_id], "limit": 10},
        )
        assert response.status_code == 200, response.text
        chat_completion = ChatCompletion(**response.json())
        assert document_id in [search.chunk.document_id for search in chat_completion.search_results]
        assert second_document_id not in [search.chunk.document_id for search in chat_completion.search_results]

    @pytest.mark.parametrize(
        "filter_type,filter_value",
        [("eq", "secondary title"), ("sw", "sec"), ("ew", "le"), ("co", "dary ti")],
        ids=["eq", "sw", "ew", "co"],
    )
    def test_tools_search_with_metadata_comparison_filters(
        self,
        client: TestClient,
        model_id: str,
        collection_id: int,
        document_id: int,
        filter_type: str,
        filter_value: str | int,
    ):
        second_document_id = self._create_document_with_chunk(
            client=client,
            collection_id=collection_id,
            chunks=[
                {"content": "Qui est Test Secondary ?", "metadata": {"source_title": "secondary title", "source_page": 1}},
                {"content": "Qui est Test Secondary ?", "metadata": {"source_title": "secondary title", "source_page": 1}},
            ],
        )

        response = self._post_chat_with_search_tool(
            client=client,
            model_id=model_id,
            query="Qui est",
            tool_args={"limit": 10, "metadata_filters": {"key": "source_title", "type": filter_type, "value": filter_value}},
        )
        assert response.status_code == 200, response.text
        chat_completion = ChatCompletion(**response.json())

        assert len(chat_completion.search_results) >= 1
        assert all(search.chunk.document_id == second_document_id for search in chat_completion.search_results)
        assert document_id not in [search.chunk.document_id for search in chat_completion.search_results]

    def test_tools_search_with_metadata_compound_filter_and(self, client: TestClient, model_id: str, collection_id: int, document_id: int):
        second_document_id = self._create_document_with_chunk(
            client=client,
            collection_id=collection_id,
            chunks=[
                {"content": "Qui est Test Secondary ?", "metadata": {"source_title": "test", "source_page": "42"}},
                {"content": "Qui est Test Secondary ?", "metadata": {"source_title": "test", "source_page": "42"}},
            ],
        )

        response = self._post_chat_with_search_tool(
            client=client,
            model_id=model_id,
            query="Qui est",
            tool_args={
                "method": "lexical",
                "limit": 10,
                "metadata_filters": {
                    "filters": [
                        {"key": "source_title", "type": "eq", "value": "test"},
                        {"key": "source_page", "type": "eq", "value": "42"},
                    ],
                    "operator": "and",
                },
            },
        )
        assert response.status_code == 200, response.text
        chat_completion = ChatCompletion(**response.json())

        assert len(chat_completion.search_results) >= 1
        assert all(search.chunk.document_id == second_document_id for search in chat_completion.search_results)
        assert document_id not in [search.chunk.document_id for search in chat_completion.search_results]

    def test_tools_search_with_metadata_compound_filter_or(self, client: TestClient, model_id: str, collection_id: int):
        second_document_id = self._create_document_with_chunk(
            client=client,
            collection_id=collection_id,
            chunks=[
                {"content": "Qui est Test Secondary ?", "metadata": {"source_title": "test", "source_page": "42"}},
                {"content": "Qui est Test Secondary ?", "metadata": {"source_title": "test", "source_page": "42"}},
            ],
        )

        response = self._post_chat_with_search_tool(
            client=client,
            model_id=model_id,
            query="Qui est",
            tool_args={
                "method": "lexical",
                "limit": 10,
                "metadata_filters": {
                    "filters": [
                        {"key": "source_page", "type": "eq", "value": "1"},
                        {"key": "source_page", "type": "eq", "value": "42"},
                    ],
                    "operator": "or",
                },
            },
        )
        assert response.status_code == 200, response.text
        chat_completion = ChatCompletion(**response.json())

        search_document_ids = {search.chunk.document_id for search in chat_completion.search_results}
        assert len(chat_completion.search_results) >= 2
        assert second_document_id in search_document_ids
        assert document_id not in search_document_ids
        assert any(search.chunk.metadata and str(search.chunk.metadata["source_page"]) == "1" for search in chat_completion.search_results)

    def test_tools_search_with_access_other_user_collection(self, client: TestClient, model_id: str):
        """Test search tool with access to other user's collection."""

        # create a collection, document and chunks with a different user
        response = client.post_with_permissions(url=f"/v1{EndpointRoute.COLLECTIONS}", json={"name": f"test_collection_{uuid4()}"})
        assert response.status_code == 201, response.text
        collection_id = response.json()["id"]

        response = client.post_with_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}", data={"collection_id": collection_id, "name": "test.pdf"})
        assert response.status_code == 201, response.text
        document_id = response.json()["id"]

        response = client.post_with_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}/{document_id}/chunks", json={"chunks": [{"content": "Test"}]})
        assert response.status_code == 201, response.text
        response = self._post_chat_with_search_tool(
            client=client,
            model_id=model_id,
            query="What is the largest planet in our solar system?",
            tool_args={"collection_ids": [collection_id], "limit": 10},
        )
        assert response.status_code == 404, response.text

        response = self._post_chat_with_search_tool(
            client=client,
            model_id=model_id,
            query="What is the largest planet in our solar system?",
            tool_args={"limit": 10},
        )
        assert response.status_code == 200, response.text
        chat_completion = ChatCompletion(**response.json())
        assert document_id not in [search.chunk.document_id for search in chat_completion.search_results]

    def test_search_tool_legacy_params(self, client: TestClient, model_id: str, document_id: int, collection_id: int):
        """Test the GET /chat/completions search unstreamed response."""
        params = {
            "model": model_id,
            "messages": [{"role": "user", "content": "Qui est Albert ?"}],
            "stream": False,
            "n": 1,
            "max_tokens": 10,
            "search": True,
            "search_args": {"collections": [collection_id], "k": 3, "method": "semantic"},
        }
        response = client.post_without_permissions(url=f"/v1{EndpointRoute.CHAT_COMPLETIONS}", json=params)

        assert response.status_code == 200, response.text

        response_json = response.json()
        ChatCompletion(**response_json)  # test output format
        assert response_json["search_results"][0]["chunk"]["document_id"] == document_id

    def test_search_tool_legacy_no_args(self, client: TestClient, model_id: str):
        """Test the GET /chat/completions search template not found."""
        params = {
            "model": model_id,
            "messages": [{"role": "user", "content": "Qui est Albert ?"}],
            "stream": False,
            "n": 1,
            "max_tokens": 10,
            "search": True,
        }
        response = client.post_without_permissions(url=f"/v1{EndpointRoute.CHAT_COMPLETIONS}", json=params)
        assert response.status_code == 422, response.text
