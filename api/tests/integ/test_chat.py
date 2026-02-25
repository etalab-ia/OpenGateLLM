import json
import logging
import os
import time
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from api.helpers._usagetokenizer import UsageTokenizer
from api.schemas.chat import ChatCompletion, ChatCompletionChunk
from api.schemas.models import ModelType
from api.utils.configuration import configuration
from api.utils.variables import EndpointRoute


@pytest.fixture(scope="module")
def setup(client: TestClient):
    # Get a language model
    response = client.get_without_permissions(url=f"/v1{EndpointRoute.MODELS}")
    assert response.status_code == 200, response.text
    response_json = response.json()

    model = [model for model in response_json["data"] if model["type"] == ModelType.TEXT_GENERATION][0]
    MODEL_ID = model["id"]

    logging.info(msg=f"test model ID: {MODEL_ID}")

    # Create a collection
    response = client.post_without_permissions(url=f"/v1{EndpointRoute.COLLECTIONS}", json={"name": f"test_collection_{uuid4()}"})
    assert response.status_code == 201, response.text
    COLLECTION_ID = response.json()["id"]

    # Upload the file to the collection
    data = {
        "collection": str(COLLECTION_ID),
        "output_format": "markdown",
        "force_ocr": "false",
        "chunk_size": "1000",
        "chunk_overlap": "200",
        "use_llm": "false",
        "paginate_output": "false",
        "chunker": "RecursiveCharacterTextSplitter",
        "chunk_min_size": "0",
        "is_separator_regex": "false",
        "metadata": json.dumps({"source_title": "test", "source_tags": "tag-1,tag-2"}),
    }

    file_path = "api/tests/integ/assets/pdf.pdf"
    with open(file_path, "rb") as file:
        files = {"file": (os.path.basename(file_path), file, "application/pdf")}
        response = client.post_without_permissions(url=f"/v1{EndpointRoute.DOCUMENTS}", data=data, files=files)
        file.close()

    assert response.status_code == 201, response.text
    DOCUMENT_ID = response.json()["id"]

    time.sleep(1)

    yield MODEL_ID, DOCUMENT_ID, COLLECTION_ID


@pytest.fixture(scope="module")
def tokenizer():
    tokenizer = UsageTokenizer(tokenizer=configuration.settings.usage_tokenizer)
    tokenizer = tokenizer.tokenizer

    yield tokenizer


@pytest.mark.usefixtures("client", "setup", "tokenizer")
class TestChat:
    @pytest.mark.asyncio
    async def test_chat_completions_unstreamed_response(self, client: TestClient, setup):
        """Test the POST /chat/completions unstreamed response."""
        MODEL_ID, DOCUMENT_ID, COLLECTION_ID = setup

        params = {"model": MODEL_ID, "messages": [{"role": "user", "content": "Hello, how are you?"}], "stream": False, "n": 1, "max_tokens": 10}
        response = client.post_without_permissions(url=f"/v1{EndpointRoute.CHAT_COMPLETIONS}", json=params)
        assert response.status_code == 200, response.text

        ChatCompletion(**response.json())  # test output format

    @pytest.mark.asyncio
    async def test_chat_completions_streamed_response(self, client: TestClient, setup):
        """Test the POST /chat/completions streamed response."""
        MODEL_ID, DOCUMENT_ID, COLLECTION_ID = setup

        params = {"model": MODEL_ID, "messages": [{"role": "user", "content": "Hello, how are you?"}], "stream": True, "n": 1, "max_tokens": 10}

        response = client.post_without_permissions(url=f"/v1{EndpointRoute.CHAT_COMPLETIONS}", json=params)
        assert response.status_code == 200, response.text

        for line in response.iter_lines():
            if line:
                chunk = line.split("data: ")[1]
                if chunk == "[DONE]":
                    break
                chunk = json.loads(chunk)
                ChatCompletionChunk(**chunk)  # test output format

    def test_chat_completions_unknown_params(self, client: TestClient, setup):
        """Test the POST /chat/completions unknown params."""
        MODEL_ID, DOCUMENT_ID, COLLECTION_ID = setup
        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
            "stream": True,
            "n": 1,
            "max_tokens": 10,
            "min_tokens": 3,  # unknown param in CreateChatCompletion schema
        }
        response = client.post_without_permissions(url=f"/v1{EndpointRoute.CHAT_COMPLETIONS}", json=params)

        assert response.status_code == 200, response.text

    def test_chat_completions_forward_error(self, client: TestClient, setup):
        """Test the POST /chat/completions forward errors from the model backend. This test works only if the model backend is vLLM."""
        MODEL_ID, DOCUMENT_ID, COLLECTION_ID = setup

        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
            "ignore_eos": 10,  # this param must be a bool (see  https://github.com/vllm-project/vllm/blob/86cbd2eee97a98df59c531c34d2aeff5a2b5765d/vllm/entrypoints/openai/protocol.py#L328)
            "stream": False,
            "n": 1,
            "max_tokens": 10,
        }
        response = client.post_without_permissions(url=f"/v1{EndpointRoute.CHAT_COMPLETIONS}", json=params)

        assert response.status_code == 400, response.text

    def test_chat_completions_usage(self, client: TestClient, setup, tokenizer):
        """Test the GET /chat/completions usage."""
        MODEL_ID, DOCUMENT_ID, COLLECTION_ID = setup
        prompt = "Hi, write a story about a cat."
        params = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 100,
        }

        prompt_tokens = len(tokenizer.encode(prompt))
        response = client.post_without_permissions(url=f"/v1{EndpointRoute.CHAT_COMPLETIONS}", json=params)
        assert response.status_code == 200, response.text

        response_json = response.json()

        assert response_json.get("usage") is not None, response.text
        assert response_json["usage"].get("prompt_tokens") is not None, response.text
        assert response_json["usage"]["prompt_tokens"] == prompt_tokens

        assert response_json["usage"].get("completion_tokens") is not None, response.text

        content = ChatCompletion.extract_response_content(response=response_json)
        completion_tokens = len(tokenizer.encode(content))
        assert response_json["usage"]["completion_tokens"] == completion_tokens

        assert response_json["usage"].get("total_tokens") is not None, response.text
        assert response_json["usage"]["total_tokens"] == prompt_tokens + completion_tokens
