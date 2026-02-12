from datetime import datetime

from httpx import AsyncClient
import pytest

from api.domain.role.entities import LimitType
from api.schemas.models import Model, Models, ModelType
from api.tests.helpers import create_token
from api.tests.integration.factories import (
    LimitSQLFactory,
    OrganizationSQLFactory,
    RouterSQLFactory,
    UserSQLFactory,
)
from api.utils.variables import EndpointRoute


@pytest.mark.asyncio(loop_scope="session")
class TestModels:
    async def test_get_models_happy_path(self, client: AsyncClient, db_session):
        organization = OrganizationSQLFactory(name="DINUM")
        user_with_routers = UserSQLFactory(name="Alice", email="alice@example.com", organization=organization)
        user_from_another_organisation = UserSQLFactory(name="Bob", email="bob@example.com")
        router_1 = RouterSQLFactory(
            user=user_with_routers,
            name="router_1",
            type=ModelType.TEXT_GENERATION,
            cost_prompt_tokens=0.001,
            cost_completion_tokens=0.002,
            providers=2,
            providers__max_context_length=2048,
            alias=["alias1_m1", "alias2_m1", "alias3_m1"],
        )
        router_2 = RouterSQLFactory(
            user=user_with_routers,
            name="router_2",
            type=ModelType.TEXT_EMBEDDINGS_INFERENCE,
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
            providers=1,
            providers__max_context_length=16384,
        )
        RouterSQLFactory(
            user=user_from_another_organisation,
            name="router_3",
            type=ModelType.TEXT_EMBEDDINGS_INFERENCE,
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
            providers=1,
        )
        LimitSQLFactory(role=user_with_routers.role, router=router_1)
        LimitSQLFactory(role=user_with_routers.role, router=router_2)

        user_1_token = await create_token(db_session, name="my_token", user=user_with_routers)
        response = await client.get(url=f"/v1{EndpointRoute.MODELS}", headers={"Authorization": f"Bearer {user_1_token.token}"})
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
        user_1 = UserSQLFactory()
        router_1 = RouterSQLFactory(
            user=user_1,
            name="router_name_1",
            type=ModelType.TEXT_GENERATION,
            cost_prompt_tokens=0.001,
            cost_completion_tokens=0.002,
            created=created,
            providers=3,
        )
        router_2 = RouterSQLFactory(
            user=user_1,
            name="router_name_2",
            type=ModelType.TEXT_EMBEDDINGS_INFERENCE,
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
            created=created,
        )
        LimitSQLFactory(role=user_1.role, router=router_1, type=LimitType.TPM, value=1000)
        LimitSQLFactory(role=user_1.role, router=router_2, type=LimitType.TPM, value=None)
        token = await create_token(db_session, name="my_token", user=user_1)

        # Act
        await db_session.flush()
        response = await client.get(url=f"/v1{EndpointRoute.MODELS}/{router_1.name}", headers={"Authorization": f"Bearer {token.token}"})
        # Assert
        actual_data = response.json()
        assert actual_data["id"] == "router_name_1"

    async def test_get_model_should_return_404_when_model_not_found(self, client: AsyncClient, db_session):
        # Arrange
        non_existent_model = "model_not_exist"
        user_1 = UserSQLFactory()
        token = await create_token(db_session, name="my_token", user=user_1)

        # Act & Assert
        await db_session.flush()
        response = await client.get(url=f"/v1{EndpointRoute.MODELS}/{non_existent_model}", headers={"Authorization": f"Bearer {token.token}"})
        # Assert
        actual_data = response.json()
        assert response.status_code == 404
        assert actual_data["detail"] == "Model not found."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
