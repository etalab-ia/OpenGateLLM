from datetime import datetime

from httpx import AsyncClient
import pytest

from api.domain.role.entities import LimitType
from api.schemas.models import Model, Models, ModelType
from api.tests.helpers import create_token
from api.tests.integration.factories import (
    LimitFactory,
    OrganizationFactory,
    ProviderFactory,
    RouterAliasFactory,
    RouterFactory,
    UserFactory,
)
from api.utils.variables import ENDPOINT__MODELS


@pytest.mark.asyncio(loop_scope="session")
class TestModels:
    async def test_get_models_happy_path(self, client: AsyncClient, db_session):
        organization = OrganizationFactory(name="DINUM")
        user_1 = UserFactory(name="Alice", email="alice@example.com", organization=organization)
        user_2 = UserFactory(name="Bob", email="bob@example.com")
        created = datetime(2024, 1, 15, 10, 30, 0)
        router_1 = RouterFactory(user=user_1, name="router_1", type=ModelType.TEXT_GENERATION, cost_prompt_tokens=0.001, cost_completion_tokens=0.002)
        router_2 = RouterFactory(
            user=user_1, name="router_2", type=ModelType.TEXT_EMBEDDINGS_INFERENCE, cost_prompt_tokens=0.0, cost_completion_tokens=0.0
        )
        router_3 = RouterFactory(
            user=user_2, name="router_3", type=ModelType.TEXT_EMBEDDINGS_INFERENCE, cost_prompt_tokens=0.0, cost_completion_tokens=0.0
        )
        ProviderFactory(router=router_1, user=user_1, model_name="m1", max_context_length=2048, vector_size=1536, created=created)
        ProviderFactory(router=router_1, user=user_1, model_name="m2", max_context_length=128000, vector_size=384, created=created)
        ProviderFactory(router=router_2, user=user_1, model_name="m3", max_context_length=16384, vector_size=1536, created=created)
        ProviderFactory(router=router_3, user=user_2, model_name="m4", max_context_length=1024, vector_size=384, created=created)
        RouterAliasFactory(router=router_1, value="alias1_m1")
        RouterAliasFactory(router=router_1, value="alias2_m1")
        RouterAliasFactory(router=router_1, value="alias3_m1")
        LimitFactory(role=user_1.role, router=router_1)
        LimitFactory(role=user_1.role, router=router_2)

        token = await create_token(db_session, name="my_token", user=user_1)
        response = await client.get(url=f"/v1{ENDPOINT__MODELS}", headers={"Authorization": f"Bearer {token.token}"})
        await db_session.flush()
        assert response.status_code == 200, f"error: retrieve models ({response.status_code})"
        models = Models(data=[Model(**model) for model in response.json()["data"]])
        assert isinstance(models, Models)
        assert all(isinstance(model, Model) for model in models.data)
        actual_data = response.json()["data"]
        expected_data = [
            {
                "aliases": ["alias1_m1", "alias2_m1", "alias3_m1"],
                "costs": {"completion_tokens": 0.002, "prompt_tokens": 0.001},
                "id": "router_1",
                "max_context_length": 2048,
                "object": "model",
                "owned_by": "DINUM",
                "type": "text-generation",
            },
            {
                "aliases": [],
                "costs": {"completion_tokens": 0.0, "prompt_tokens": 0.0},
                "id": "router_2",
                "max_context_length": 16384,
                "object": "model",
                "owned_by": "DINUM",
                "type": "text-embeddings-inference",
            },
        ]

        actual_without_created = [{k: v for k, v in item.items() if k != "created"} for item in actual_data]

        assert actual_without_created == expected_data

    async def test_get_model_by_name_should_return_specific_model(self, client: AsyncClient, db_session):
        # Arrange
        created = datetime(2024, 1, 15, 10, 30, 0)

        user_1 = UserFactory()

        router_1 = RouterFactory(
            user=user_1, name="router_name_1", type=ModelType.TEXT_GENERATION, cost_prompt_tokens=0.001, cost_completion_tokens=0.002, created=created
        )
        router_2 = RouterFactory(
            user=user_1,
            name="router_name_2",
            type=ModelType.TEXT_EMBEDDINGS_INFERENCE,
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
            created=created,
        )
        ProviderFactory(router=router_1, user=user_1, model_name="m1", max_context_length=2048, vector_size=1536, created=created)
        ProviderFactory(router=router_1, user=user_1, model_name="m2", max_context_length=128000, vector_size=384, created=created)
        ProviderFactory(router=router_2, user=user_1, model_name="m3", max_context_length=16384, vector_size=1536, created=created)
        LimitFactory(role=user_1.role, router=router_1, type=LimitType.TPM, value=1000)
        LimitFactory(role=user_1.role, router=router_2, type=LimitType.TPM, value=None)
        token = await create_token(db_session, name="my_token", user=user_1)

        # Act
        await db_session.flush()
        response = await client.get(url=f"/v1{ENDPOINT__MODELS}/{router_1.name}", headers={"Authorization": f"Bearer {token.token}"})
        # Assert
        actual_data = response.json()
        assert actual_data["id"] == "router_name_1"

    async def test_get_model_should_return_404_when_model_not_found(self, client: AsyncClient, db_session):
        # Arrange
        created = datetime(2024, 1, 15, 10, 30, 0)
        non_existent_model = "model_not_exist"
        user_1 = UserFactory()

        router_1 = RouterFactory(
            user=user_1, name="router_name_1", type=ModelType.TEXT_GENERATION, cost_prompt_tokens=0.001, cost_completion_tokens=0.002, created=created
        )
        ProviderFactory(router=router_1, user=user_1, model_name="m1", max_context_length=2048, vector_size=1536, created=created)
        LimitFactory(role=user_1.role, router=router_1, type=LimitType.TPM, value=1000)
        token = await create_token(db_session, name="my_token", user=user_1)

        # Act & Assert
        response = await client.get(url=f"/v1{ENDPOINT__MODELS}/{non_existent_model}", headers={"Authorization": f"Bearer {token.token}"})
        # Assert
        actual_data = response.json()
        assert response.status_code == 404
        assert actual_data["detail"] == "Model not found."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
