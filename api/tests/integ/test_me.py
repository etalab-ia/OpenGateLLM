from asyncio import sleep
import datetime as dt
import time

from fastapi.testclient import TestClient
import pytest

from api.domain.provider.entities import ProviderType
from api.infrastructure.fastapi.schemas.usage import UsagesResponse
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
from api.utils.variables import EndpointRoute


@pytest.fixture(scope="module")
def setup_model_and_user(client: TestClient):
    test_id = generate_test_id(prefix="TestUsage")
    process = run_openmockllm(test_id=test_id, backend="mistral")
    try:
        router_id = create_router(model_name=process.model_name, model_type=ModelType.TEXT_GENERATION, client=client)
        create_provider(
            router_id=router_id,
            provider_url=process.url,
            provider_key=None,
            provider_name=process.model_name,
            provider_type=ProviderType.MISTRAL,
            model_total_params=100,
            model_active_params=100,
            client=client,
        )
        role_id = create_role(router_id=router_id, client=client)
        user_id = create_user(role_id=role_id, client=client)
        _, key = create_token(user_id=user_id, token_name=f"test-token-{dt.datetime.now().strftime('%Y%m%d%H%M%S')}", client=client)

        yield key, process.model_name
    except Exception as e:
        raise e
    finally:
        kill_openmockllm(process=process)


def _get_usage(client: TestClient, key: str, start_time: int) -> UsagesResponse:
    response = client.get(
        url=f"/v1{EndpointRoute.USAGE}",
        headers={"Authorization": f"Bearer {key}"},
        params={"start_time": start_time, "end_time": int(time.time()) + 1},
    )
    assert response.status_code == 200, response.text
    return UsagesResponse(**response.json())


def _assert_single_chat_bucket(usages: UsagesResponse) -> None:
    assert usages.object == "list"
    assert usages.total == 1
    assert len(usages.data) == 1
    bucket = usages.data[0]
    assert bucket.object == "usage.bucket"
    assert bucket.requests == 1
    assert bucket.prompt_tokens > 0
    assert bucket.completion_tokens > 0
    assert bucket.total_tokens == bucket.prompt_tokens + bucket.completion_tokens


@pytest.mark.usefixtures("client")
class TestUsage:
    @pytest.mark.asyncio
    async def test_get_me_usage_stream_response(self, client: TestClient, setup_model_and_user):
        """Test that authenticated accounts can access their usage data"""

        key, model_name = setup_model_and_user

        # chat completion
        start_time = int(time.time())
        response = client.post(
            url=f"/v1{EndpointRoute.CHAT_COMPLETIONS}",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": model_name, "messages": [{"role": "user", "content": "Hello, how are you?"}], "stream": True},
        )
        assert response.status_code == 200, response.text
        chunks = list()
        for chunk in response.iter_lines():
            chunks.append(chunk)
        await sleep(2)

        _assert_single_chat_bucket(_get_usage(client, key, start_time))

    @pytest.mark.asyncio
    async def test_get_me_usage_unstream_response(self, client: TestClient, setup_model_and_user):
        """Test that authenticated accounts can access their usage data"""

        key, model_name = setup_model_and_user

        # chat completion
        start_time = int(time.time())
        response = client.post(
            url=f"/v1{EndpointRoute.CHAT_COMPLETIONS}",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": model_name, "messages": [{"role": "user", "content": "Hello, how are you?"}]},
        )
        response.raise_for_status()
        response.json()
        await sleep(2)

        _assert_single_chat_bucket(_get_usage(client, key, start_time))
