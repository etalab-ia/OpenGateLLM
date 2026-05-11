from unittest.mock import AsyncMock

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import get_models_use_case_factory
from api.domain.model.errors import ModelNotFoundError
from api.domain.user.errors import UserExpiredError
from api.schemas.models import ModelType
from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.factories.sql import LimitSQLFactory, RouterSQLFactory, UserSQLFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.MODELS}"


@pytest.mark.asyncio(loop_scope="session")
class TestGetModels:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.user = UserSQLFactory(name="Alice", email="alice@example.com")
        self.key = await create_key(db_session, name="admin_key", user=self.user)
        self.router_owner = UserSQLFactory(name="Bob", email="bob@example.com", admin_user=True)

    async def test_happy_path(self, client: AsyncClient, db_session):
        router_1 = RouterSQLFactory(
            user=self.router_owner,
            name="router_1",
            type=ModelType.TEXT_GENERATION,
            cost_prompt_tokens=0.001,
            cost_completion_tokens=0.002,
            providers=2,
            providers__max_context_length=2048,
            alias=["alias1_m1", "alias2_m1", "alias3_m1"],
        )
        router_2 = RouterSQLFactory(
            user=self.router_owner,
            name="router_2",
            type=ModelType.TEXT_EMBEDDINGS_INFERENCE,
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
            providers=1,
            providers__max_context_length=16384,
        )
        LimitSQLFactory(role=self.user.role, router=router_1)
        LimitSQLFactory(role=self.user.role, router=router_2)

        await db_session.flush()

        response = await client.get(url=URL, headers={"Authorization": f"Bearer {self.key.token}"})
        assert response.status_code == 200, f"error: retrieve models ({response.status_code})"

        data = response.json()
        assert data["object"] == "list"
        assert len(data["data"]) == 2

        models_by_id = {model["id"]: model for model in data["data"]}

        assert models_by_id["router_1"]["type"] == ModelType.TEXT_GENERATION.value
        assert sorted(models_by_id["router_1"]["aliases"]) == ["alias1_m1", "alias2_m1", "alias3_m1"]
        assert models_by_id["router_1"]["costs"] == {"prompt_tokens": 0.001, "completion_tokens": 0.002}
        assert models_by_id["router_1"]["max_context_length"] == 2048

        assert models_by_id["router_2"]["type"] == ModelType.TEXT_EMBEDDINGS_INFERENCE.value
        assert models_by_id["router_2"]["aliases"] == []
        assert models_by_id["router_2"]["costs"] == {"prompt_tokens": 0.0, "completion_tokens": 0.0}
        assert models_by_id["router_2"]["max_context_length"] == 16384

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (
                UserExpiredError(),
                403,
                "Your account has expired. Please contact support to renew your account.",
            ),
        ],
    )
    async def test_error_maps_to_correct_http_status(self, client: AsyncClient, app, use_case_result, expected_status, expected_detail):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[get_models_use_case_factory] = lambda: mock_use_case

        response = await client.get(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
        )

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail

    @pytest.mark.parametrize(
        "headers,expected_status,expected_detail",
        [
            ({}, 401, "Not authenticated"),
            ({"Authorization": "Bearer malformed-token"}, 401, "Invalid API key."),
            ({"Authorization": f"Bearer {INVALID_API_KEY}"}, 401, "Invalid API key."),
        ],
    )
    async def test_auth(self, client: AsyncClient, headers, expected_status, expected_detail):
        response = await client.get(url=URL, headers=headers)

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail


@pytest.mark.asyncio(loop_scope="session")
class TestGetModel:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.user = UserSQLFactory(name="Alice", email="alice@example.com")
        self.key = await create_key(db_session, name="admin_key", user=self.user)
        self.router_owner = UserSQLFactory(name="Bob", email="bob@example.com", admin_user=True)

    async def test_happy_path(self, client: AsyncClient, db_session):
        router_1 = RouterSQLFactory(
            user=self.router_owner,
            name="router_1",
            type=ModelType.TEXT_GENERATION,
            cost_prompt_tokens=0.001,
            cost_completion_tokens=0.002,
            providers=2,
            providers__max_context_length=2048,
            alias=["alias1_m1", "alias2_m1", "alias3_m1"],
        )
        router_2 = RouterSQLFactory(
            user=self.router_owner,
            name="router_2",
            type=ModelType.TEXT_EMBEDDINGS_INFERENCE,
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
            providers=1,
            providers__max_context_length=16384,
        )
        LimitSQLFactory(role=self.user.role, router=router_1)
        LimitSQLFactory(role=self.user.role, router=router_2)

        # Act
        await db_session.flush()
        response = await client.get(url=f"{URL}/{router_1.name}", headers={"Authorization": f"Bearer {self.key.token}"})
        # Assert
        actual_data = response.json()
        assert actual_data["id"] == "router_1"
        assert actual_data["type"] == ModelType.TEXT_GENERATION.value
        assert actual_data["aliases"] == ["alias1_m1", "alias2_m1", "alias3_m1"]
        assert actual_data["costs"] == {"prompt_tokens": 0.001, "completion_tokens": 0.002}
        assert actual_data["max_context_length"] == 2048

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (
                UserExpiredError(),
                403,
                "Your account has expired. Please contact support to renew your account.",
            ),
            (
                ModelNotFoundError(),
                404,
                "Model not found.",
            ),
        ],
    )
    async def test_error_maps_to_correct_http_status(self, client: AsyncClient, app, use_case_result, expected_status, expected_detail):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[get_models_use_case_factory] = lambda: mock_use_case

        response = await client.get(
            url=f"{URL}/non_existent_model",
            headers={"Authorization": f"Bearer {self.key.token}"},
        )

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail

    @pytest.mark.parametrize(
        "headers,expected_status,expected_detail",
        [
            ({}, 401, "Not authenticated"),
            ({"Authorization": "Bearer malformed-token"}, 401, "Invalid API key."),
            ({"Authorization": f"Bearer {INVALID_API_KEY}"}, 401, "Invalid API key."),
        ],
    )
    async def test_auth(self, client: AsyncClient, headers, expected_status, expected_detail):
        response = await client.get(url=f"{URL}/non_existent_model", headers=headers)

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
