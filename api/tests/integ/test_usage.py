import datetime as dt
from time import sleep

from fastapi.testclient import TestClient
import pytest

from api.schemas.accounts import AccountUsages
from api.schemas.admin.providers import ProviderType
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
from api.utils.variables import ENDPOINT__CHAT_COMPLETIONS, ENDPOINT__USAGE


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
        key_id, key = create_token(user_id=user_id, token_name=f"test-token-{dt.datetime.now().strftime("%Y%m%d%H%M%S")}", client=client)

        yield user_id, key_id, key, process.model_name
    except Exception as e:
        raise e
    finally:
        kill_openmockllm(process=process)


@pytest.mark.usefixtures("client")
class TestUsage:
    @pytest.mark.asyncio
    async def test_get_usage(self, client: TestClient, setup_model_and_user):
        """Test that authenticated accounts can access their usage data"""

        user_id, key_id, key, model_name = setup_model_and_user

        # chat completion
        response = client.post(
            url=f"/v1{ENDPOINT__CHAT_COMPLETIONS}",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": model_name, "messages": [{"role": "user", "content": "Hello, how are you?"}]},
        )
        assert response.status_code == 200, response.text

        sleep(2)

        # get usage
        response = client.get(url=f"/v1{ENDPOINT__USAGE}", headers={"Authorization": f"Bearer {key}"})
        assert response.status_code == 200, response.text
        data = response.json()
        usages = AccountUsages(**data)

        assert len(usages.data) == 1
        assert usages.total == 1
        assert usages.has_more is False
        assert usages.data[0].user_id == user_id
        assert usages.data[0].token_id == key_id
        assert usages.data[0].endpoint == f"/v1{ENDPOINT__CHAT_COMPLETIONS}"
        assert usages.data[0].method == "POST"
        assert usages.data[0].model == model_name
