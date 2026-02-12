from httpx import AsyncClient
import pytest

from api.domain.router.entities import RouterLoadBalancingStrategy
from api.schemas.models import ModelType
from api.tests.helpers import create_token
from api.tests.integration.factories import (
    RouterSQLFactory,
    UserSQLFactory,
)
from api.utils.variables import EndpointRoute


@pytest.mark.asyncio(loop_scope="session")
class TestAdminCreateRouter:
    async def test_create_router_happy_path(self, client: AsyncClient, db_session):
        # Arrange
        admin_user = UserSQLFactory(admin_user=True)
        token = await create_token(db_session, name="admin_token", user=admin_user)

        router_data = {
            "name": "test-router-1",
            "type": "text-generation",
            "aliases": ["alias_1", "alias_2"],
            "load_balancing_strategy": "shuffle",
            "cost_prompt_tokens": 0.001,
            "cost_completion_tokens": 0.002,
        }

        await db_session.flush()

        # Act
        response = await client.post(
            url=f"/v1{EndpointRoute.ADMIN_ROUTERS}",
            headers={"Authorization": f"Bearer {token.token}"},
            json=router_data,
        )

        # Assert
        response_json = response.json()
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        assert isinstance(response_json.get("id"), int)
        assert response_json.get("aliases") == ["alias_1", "alias_2"]

    async def test_create_router_requires_admin_permission(self, client: AsyncClient, db_session):
        # Arrange
        regular_user = UserSQLFactory(regular_user=True)
        token = await create_token(db_session, name="user_token", user=regular_user)

        router_data = {
            "name": "unauthorized-router",
            "type": "text-generation",
            "aliases": [],
            "load_balancing_strategy": "shuffle",
            "cost_prompt_tokens": 0.001,
            "cost_completion_tokens": 0.002,
        }

        # Act
        response = await client.post(
            url=f"/v1{EndpointRoute.ADMIN_ROUTERS}",
            headers={"Authorization": f"Bearer {token.token}"},
            json=router_data,
        )

        # Assert
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        assert response.json().get("detail") == "Insufficient rights."

    async def test_create_router_with_duplicate_name(self, client: AsyncClient, db_session):
        # Arrange
        duplicate_name = "duplicate-name"
        admin_user = UserSQLFactory(admin_user=True)

        RouterSQLFactory(
            user=admin_user,
            name=duplicate_name,
            type=ModelType.TEXT_GENERATION,
        )
        await db_session.flush()

        token = await create_token(db_session, name="admin_token", user=admin_user)

        router_data = {
            "name": duplicate_name,
            "type": ModelType.TEXT_GENERATION,
            "aliases": [],
            "load_balancing_strategy": "shuffle",
            "cost_prompt_tokens": 0.001,
            "cost_completion_tokens": 0.002,
        }

        # Act
        response = await client.post(
            url=f"/v1{EndpointRoute.ADMIN_ROUTERS}",
            headers={"Authorization": f"Bearer {token.token}"},
            json=router_data,
        )

        # Assert
        assert response.status_code in [400, 409], f"Expected 400 or 409, got {response.status_code}"
        assert response.json().get("detail") == f"Router '{duplicate_name}' already exists."

    async def test_create_router_with_duplicate_alias(self, client: AsyncClient, db_session):
        # Arrange
        admin_user = UserSQLFactory(admin_user=True)
        duplicate_alias = "duplicate-alias"
        RouterSQLFactory(user=admin_user, name="existing-router", type=ModelType.TEXT_GENERATION, alias=[duplicate_alias])
        await db_session.flush()

        token = await create_token(db_session, name="admin_token", user=admin_user)

        router_data = {
            "name": "new-router",
            "type": ModelType.TEXT_GENERATION.value,
            "aliases": [duplicate_alias],
            "load_balancing_strategy": RouterLoadBalancingStrategy.SHUFFLE.value,
            "cost_prompt_tokens": 0.001,
            "cost_completion_tokens": 0.002,
        }

        # Act
        response = await client.post(
            url=f"/v1{EndpointRoute.ADMIN_ROUTERS}",
            headers={"Authorization": f"Bearer {token.token}"},
            json=router_data,
        )

        # Assert
        assert response.status_code in [400, 409], f"Expected 400 or 409, got {response.status_code}"
        assert response.json().get("detail") == f"Following aliases already exist: '['{duplicate_alias}']'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
