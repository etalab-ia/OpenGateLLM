from asyncio import sleep
import datetime as dt
import time

from fastapi.testclient import TestClient
import pytest

from api.schemas.admin.providers import ProviderType
from api.schemas.me.usage import Usages
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
from api.utils.variables import ENDPOINT__CHAT_COMPLETIONS, ENDPOINT__ME_USAGE


@pytest.fixture(scope="module")
def setup_model_and_user(client: TestClient):
    test_id = generate_test_id(prefix="TestUsage")
    process = run_openmockllm(test_id=test_id, backend="vllm")
    try:
        router_id = create_router(model_name=process.model_name, model_type=ModelType.TEXT_GENERATION, client=client)
        create_provider(
            router_id=router_id,
            provider_url=process.url,
            provider_key=None,
            provider_name=process.model_name,
            provider_type=ProviderType.VLLM,
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


@pytest.mark.usefixtures("client")
class TestUsage:
    @pytest.mark.asyncio
    async def test_get_me_usage_stream_response(self, client: TestClient, setup_model_and_user):
        """Test that authenticated accounts can access their usage data"""

        key, model_name = setup_model_and_user

        # chat completion
        start_time = int(time.time())
        response = client.post(
            url=f"/v1{ENDPOINT__CHAT_COMPLETIONS}",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": model_name, "messages": [{"role": "user", "content": "Hello, how are you?"}], "stream": True},
        )
        assert response.status_code == 200, response.text
        chunks = list()
        for chunk in response.iter_lines():
            chunks.append(chunk)
        await sleep(2)

        # get usage
        response = client.get(url=f"/v1{ENDPOINT__ME_USAGE}", headers={"Authorization": f"Bearer {key}"}, params={"start_time": start_time})
        assert response.status_code == 200, response.text
        data = response.json()
        usages = Usages(**data)

        assert len(usages.data) == 1
        assert usages.data[0].endpoint == f"/v1{ENDPOINT__CHAT_COMPLETIONS}"
        assert usages.data[0].model == model_name
        assert usages.data[0].usage.prompt_tokens is not None
        assert usages.data[0].usage.completion_tokens is not None
        assert usages.data[0].usage.total_tokens is not None
        assert usages.data[0].usage.metrics.latency is not None
        assert usages.data[0].usage.metrics.ttft is not None

    @pytest.mark.asyncio
    async def test_get_me_usage_unstream_response(self, client: TestClient, setup_model_and_user):
        """Test that authenticated accounts can access their usage data"""

        key, model_name = setup_model_and_user

        # chat completion
        start_time = int(time.time())
        response = client.post(
            url=f"/v1{ENDPOINT__CHAT_COMPLETIONS}",
            headers={"Authorization": f"Bearer aw{key}"},
            json={"model": model_name, "messages": [{"role": "user", "content": "Hello, how are you?"}]},
        )
        response.raise_for_status()
        response.json()
        await sleep(2)

        response = client.get(url=f"/v1{ENDPOINT__ME_USAGE}", headers={"Authorization": f"Bearer {key}"}, params={"start_time": start_time})
        assert response.status_code == 200, response.text
        data = response.json()
        usages = Usages(**data)

        assert len(usages.data) == 1
        assert usages.data[0].endpoint == f"/v1{ENDPOINT__CHAT_COMPLETIONS}"
        assert usages.data[0].model == model_name
        assert usages.data[0].usage.prompt_tokens is not None
        assert usages.data[0].usage.completion_tokens is not None
        assert usages.data[0].usage.total_tokens is not None
        assert usages.data[0].usage.metrics.latency is not None
        assert usages.data[0].usage.metrics.ttft is None  # no stream, so no ttft
