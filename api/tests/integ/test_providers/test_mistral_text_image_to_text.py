import datetime as dt
import json

from fastapi.testclient import TestClient
import pytest

from api.helpers._usagetokenizer import UsageTokenizer
from api.schemas.admin.providers import ProviderType
from api.schemas.chat import ChatCompletion, ChatCompletionChunk
from api.schemas.models import ModelType
from api.tests.integ.utils import (
    create_provider,
    create_role,
    create_router,
    create_token,
    create_user,
    generate_test_id,
    kill_openmockllm,
    run_openmockllm,
)
from api.utils.configuration import configuration
from api.utils.variables import ENDPOINT__CHAT_COMPLETIONS


@pytest.fixture(scope="module")
def setup_mistral_image_text_to_text(client: TestClient):
    test_id = generate_test_id(prefix="TestMistralTextImageToText")
    process = run_openmockllm(test_id=test_id, backend="mistral")
    try:
        router_id = create_router(model_name=process.model_name, model_type=ModelType.IMAGE_TEXT_TO_TEXT, client=client)
        create_provider(
            router_id=router_id,
            provider_url=process.url,
            provider_key=None,
            provider_name=process.model_name,
            provider_type=ProviderType.MISTRAL,
            client=client,
        )
        role_id = create_role(router_id=router_id, client=client)
        user_id = create_user(role_id=role_id, client=client)
        _, key = create_token(user_id=user_id, token_name=f"test-token-{dt.datetime.now().strftime("%Y%m%d%H%M%S")}", client=client)

        yield key, process.model_name
    except Exception as e:
        raise e
    finally:
        kill_openmockllm(process=process)


@pytest.fixture(scope="module")
def tokenizer():
    tokenizer = UsageTokenizer(tokenizer=configuration.settings.usage_tokenizer)
    tokenizer = tokenizer.tokenizer

    yield tokenizer


@pytest.mark.usefixtures("client", "setup_mistral_image_text_to_text")
class TestMistralImageTextToText:
    def test_mistral_image_text_to_text_unstreamed_response(self, client: TestClient, setup_mistral_image_text_to_text: tuple[str, str]):
        """Test the POST /chat/completions unstreamed response."""
        key, model_name = setup_mistral_image_text_to_text

        params = {
            "model": model_name,
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
            "stream": False,
            "n": 1,
            "max_tokens": 10,
        }
        response = client.post(url=f"/v1{ENDPOINT__CHAT_COMPLETIONS}", json=params, headers={"Authorization": f"Bearer {key}"})
        assert response.status_code == 200, response.text
        ChatCompletion(**response.json())  # test output format

    def test_mistral_image_text_to_text_streamed_response(self, client: TestClient, setup_mistral_image_text_to_text: tuple[str, str]):
        """Test the POST /chat/completions streamed response."""
        key, model_name = setup_mistral_image_text_to_text

        params = {"model": model_name, "messages": [{"role": "user", "content": "Hello, how are you?"}], "stream": True, "n": 1, "max_tokens": 10}

        response = client.post(url=f"/v1{ENDPOINT__CHAT_COMPLETIONS}", json=params, headers={"Authorization": f"Bearer {key}"})
        assert response.status_code == 200, response.text

        for line in response.iter_lines():
            if line:
                chunk = line.split("data: ")[1]
                if chunk == "[DONE]":
                    break
                chunk = json.loads(chunk)
                ChatCompletionChunk(**chunk)  # test output format

    def test_chat_completions_unknown_params(self, client: TestClient, setup_mistral_image_text_to_text: tuple[str, str]):
        """Test the POST /chat/completions unknown params."""
        key, model_name = setup_mistral_image_text_to_text
        params = {
            "model": model_name,
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
            "stream": True,
            "n": 1,
            "max_tokens": 10,
            "min_tokens": 3,  # unknown param in CreateChatCompletion schema
        }
        response = client.post(url=f"/v1{ENDPOINT__CHAT_COMPLETIONS}", json=params, headers={"Authorization": f"Bearer {key}"})

        assert response.status_code == 200, response.text

    def test_chat_completions_usage(self, client: TestClient, setup_mistral_image_text_to_text: tuple[str, str], tokenizer):
        """Test the GET /chat/completions usage."""
        key, model_name = setup_mistral_image_text_to_text
        prompt = "Hi, write a story."
        params = {"model": model_name, "messages": [{"role": "user", "content": prompt}], "max_tokens": 10}

        prompt_tokens = len(tokenizer.encode(prompt))
        response = client.post(url=f"/v1{ENDPOINT__CHAT_COMPLETIONS}", json=params)
        assert response.status_code == 200, response.text

        response_json = response.json()

        assert response_json.get("usage") is not None, response.text
        assert response_json["usage"].get("prompt_tokens") is not None, response.text
        assert response_json["usage"]["prompt_tokens"] == prompt_tokens

        assert response_json["usage"].get("completion_tokens") is not None, response.text

        contents = [choice.get("message", {}).get("content", "") for choice in response_json.get("choices", [])]
        completion_tokens = sum([len(tokenizer.encode(content)) for content in contents])
        assert response_json["usage"]["completion_tokens"] == completion_tokens

        assert response_json["usage"].get("total_tokens") is not None, response.text
        assert response_json["usage"]["total_tokens"] == prompt_tokens + completion_tokens
