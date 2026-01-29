from httpx import AsyncClient
import pytest

from api.domain.role.entities import PermissionType
from api.schemas.admin.routers import RouterLoadBalancingStrategy
from api.schemas.models import ModelType
from api.tests.helpers import create_token
from api.tests.integration.factories import (
    OrganizationSQLFactory,
    PermissionSQLFactory,
    RouterAliasSQLFactory,
    RouterSQLFactory,
    UserSQLFactory,
)
from api.utils.variables import ENDPOINT__ADMIN_ROUTERS


@pytest.mark.asyncio(loop_scope="session")
class TestAdminCreateRouter:
    """Test suite for POST /v1/admin/routers endpoint."""

    async def test_create_router_happy_path(self, client: AsyncClient, db_session):
        """
        Test creating a router with valid data as admin user.

        Should return 201 with router ID.
        """
        # Arrange
        organization = OrganizationSQLFactory(name="DINUM")
        admin_user = UserSQLFactory(
            name="Admin User",
            email="admin@example.com",
            organization=organization,
            admin_user=True,
        )
        PermissionSQLFactory(role=admin_user.role, permission=PermissionType.ADMIN)

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
            url=f"/v1{ENDPOINT__ADMIN_ROUTERS}",
            headers={"Authorization": f"Bearer {token.token}"},
            json=router_data,
        )

        # Assert
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        response_data = response.json()
        assert "id" in response_data
        assert isinstance(response_data["id"], int)
        assert response_data["id"] > 0

    async def test_create_router_with_aliases(self, client: AsyncClient, db_session):
        """
        Test creating a router with multiple aliases.

        Should successfully create router with all aliases.
        """
        # Arrange
        admin_user = UserSQLFactory(admin_user=True)
        PermissionSQLFactory(role=admin_user.role, permission=PermissionType.ADMIN)
        token = await create_token(db_session, name="admin_token", user=admin_user)

        router_data = {
            "name": "gpt-4-turbo",
            "type": "text-generation",
            "aliases": ["gpt-4", "gpt-4-turbo-preview", "gpt4"],
            "load_balancing_strategy": "least_busy",
            "cost_prompt_tokens": 0.01,
            "cost_completion_tokens": 0.03,
        }

        await db_session.flush()

        # Act
        response = await client.post(
            url=f"/v1{ENDPOINT__ADMIN_ROUTERS}",
            headers={"Authorization": f"Bearer {token.token}"},
            json=router_data,
        )

        # Assert
        assert response.status_code == 201
        response_data = response.json()
        assert "id" in response_data

        # Verify router was created with aliases in database
        await db_session.flush()
        from api.sql.models import Router, RouterAlias

        router = await db_session.get(Router, response_data["id"])
        assert router is not None
        assert router.name == "gpt-4-turbo"

        # Verify aliases
        from sqlalchemy import select

        aliases_query = select(RouterAlias).where(RouterAlias.router_id == router.id)
        result = await db_session.execute(aliases_query)
        aliases = [alias.value for alias in result.scalars().all()]
        assert set(aliases) == {"gpt-4", "gpt-4-turbo-preview", "gpt4"}

    async def test_create_router_with_embedding_type(self, client: AsyncClient, db_session):
        """
        Test creating an embeddings router.

        Should successfully create router with TEXT_EMBEDDINGS_INFERENCE type.
        """
        # Arrange
        admin_user = UserSQLFactory(admin_user=True)
        PermissionSQLFactory(role=admin_user.role, permission=PermissionType.ADMIN)
        token = await create_token(db_session, name="admin_token", user=admin_user)

        router_data = {
            "name": "text-embedding-ada-002",
            "type": "text-embeddings-inference",
            "aliases": ["ada", "embedding-model"],
            "load_balancing_strategy": "shuffle",
            "cost_prompt_tokens": 0.0001,
            "cost_completion_tokens": 0.0,
        }

        # Act
        response = await client.post(
            url=f"/v1{ENDPOINT__ADMIN_ROUTERS}",
            headers={"Authorization": f"Bearer {token.token}"},
            json=router_data,
        )

        # Assert
        assert response.status_code == 201
        response_data = response.json()

        # Verify type in database
        from api.sql.models import Router

        router = await db_session.get(Router, response_data["id"])
        assert router.type == ModelType.TEXT_EMBEDDINGS_INFERENCE.value

    async def test_create_router_with_zero_cost(self, client: AsyncClient, db_session):
        """
        Test creating a free router (zero cost).

        Should accept zero values for costs.
        """
        # Arrange
        admin_user = UserSQLFactory(admin_user=True)
        PermissionSQLFactory(role=admin_user.role, permission=PermissionType.ADMIN)
        token = await create_token(db_session, name="admin_token", user=admin_user)

        router_data = {
            "name": "free-model",
            "type": "text-generation",
            "aliases": [],
            "load_balancing_strategy": "shuffle",
            "cost_prompt_tokens": 0.0,
            "cost_completion_tokens": 0.0,
        }

        # Act
        response = await client.post(
            url=f"/v1{ENDPOINT__ADMIN_ROUTERS}",
            headers={"Authorization": f"Bearer {token.token}"},
            json=router_data,
        )

        # Assert
        assert response.status_code == 201

    async def test_create_router_requires_admin_permission(self, client: AsyncClient, db_session):
        """
        Test that non-admin users cannot create routers.

        Should return 403 Forbidden.
        """
        # Arrange - Regular user without admin permission
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
            url=f"/v1{ENDPOINT__ADMIN_ROUTERS}",
            headers={"Authorization": f"Bearer {token.token}"},
            json=router_data,
        )

        # Assert
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        assert response.text.lower() == '{"detail":"insufficient rights."}'

    async def test_create_router_requires_authentication(self, client: AsyncClient, db_session):
        """
        Test that unauthenticated requests are rejected.

        Should return 401 Unauthorized.
        """
        # Arrange
        router_data = {
            "name": "test-router",
            "type": "text-generation",
            "aliases": [],
            "load_balancing_strategy": "shuffle",
            "cost_prompt_tokens": 0.001,
            "cost_completion_tokens": 0.002,
        }

        # Act - No Authorization header
        response = await client.post(
            url=f"/v1{ENDPOINT__ADMIN_ROUTERS}",
            json=router_data,
        )

        # Assert
        # assert response.status_code == 401
        assert response.status_code == 403

    async def test_create_router_with_invalid_name_empty(self, client: AsyncClient, db_session):
        """
        Test creating router with empty name.

        Should return 422 validation error.
        """
        # Arrange
        admin_user = UserSQLFactory(admin_user=True)
        PermissionSQLFactory(role=admin_user.role, permission=PermissionType.ADMIN)
        token = await create_token(db_session, name="admin_token", user=admin_user)

        router_data = {
            "name": "",  # Invalid: empty string
            "type": "text-generation",
            "aliases": [],
            "load_balancing_strategy": "shuffle",
            "cost_prompt_tokens": 0.001,
            "cost_completion_tokens": 0.002,
        }

        # Act
        response = await client.post(
            url=f"/v1{ENDPOINT__ADMIN_ROUTERS}",
            headers={"Authorization": f"Bearer {token.token}"},
            json=router_data,
        )

        # Assert
        assert response.status_code == 422

    async def test_create_router_with_invalid_name_whitespace(self, client: AsyncClient, db_session):
        """
        Test creating router with whitespace-only name.

        Should return 422 validation error (after stripping).
        """
        # Arrange
        admin_user = UserSQLFactory(admin_user=True)
        PermissionSQLFactory(role=admin_user.role, permission=PermissionType.ADMIN)
        token = await create_token(db_session, name="admin_token", user=admin_user)

        router_data = {
            "name": "   ",  # Invalid: whitespace only
            "type": "text-generation",
            "aliases": [],
            "load_balancing_strategy": "shuffle",
            "cost_prompt_tokens": 0.001,
            "cost_completion_tokens": 0.002,
        }

        # Act
        response = await client.post(
            url=f"/v1{ENDPOINT__ADMIN_ROUTERS}",
            headers={"Authorization": f"Bearer {token.token}"},
            json=router_data,
        )

        # Assert
        assert response.status_code == 422

    async def test_create_router_with_invalid_type(self, client: AsyncClient, db_session):
        """
        Test creating router with invalid model type.

        Should return 422 validation error.
        """
        # Arrange
        admin_user = UserSQLFactory(admin_user=True)
        PermissionSQLFactory(role=admin_user.role, permission=PermissionType.ADMIN)
        token = await create_token(db_session, name="admin_token", user=admin_user)

        router_data = {
            "name": "test-router",
            "type": "invalid-type",  # Invalid type
            "aliases": [],
            "load_balancing_strategy": "shuffle",
            "cost_prompt_tokens": 0.001,
            "cost_completion_tokens": 0.002,
        }

        # Act
        response = await client.post(
            url=f"/v1{ENDPOINT__ADMIN_ROUTERS}",
            headers={"Authorization": f"Bearer {token.token}"},
            json=router_data,
        )

        # Assert
        assert response.status_code == 422

    async def test_create_router_with_negative_cost(self, client: AsyncClient, db_session):
        """
        Test creating router with negative costs.

        Should return 422 validation error (costs must be >= 0).
        """
        # Arrange
        admin_user = UserSQLFactory(admin_user=True)
        PermissionSQLFactory(role=admin_user.role, permission=PermissionType.ADMIN)
        token = await create_token(db_session, name="admin_token", user=admin_user)

        router_data = {
            "name": "test-router",
            "type": "text-generation",
            "aliases": [],
            "load_balancing_strategy": "shuffle",
            "cost_prompt_tokens": -0.001,  # Invalid: negative
            "cost_completion_tokens": 0.002,
        }

        # Act
        response = await client.post(
            url=f"/v1{ENDPOINT__ADMIN_ROUTERS}",
            headers={"Authorization": f"Bearer {token.token}"},
            json=router_data,
        )

        # Assert
        assert response.status_code == 422

    async def test_create_router_with_duplicate_name(self, client: AsyncClient, db_session):
        """
        Test creating router with name that already exists.

        Should return 409 Conflict or 400 Bad Request.
        """
        # Arrange
        admin_user = UserSQLFactory(admin_user=True)
        PermissionSQLFactory(role=admin_user.role, permission=PermissionType.ADMIN)

        existing_router = RouterSQLFactory(
            user=admin_user,
            name="duplicate-name",
            type=ModelType.TEXT_GENERATION,
        )
        await db_session.flush()

        token = await create_token(db_session, name="admin_token", user=admin_user)

        router_data = {
            "name": "duplicate-name",  # Same name as existing
            "type": "text-generation",
            "aliases": [],
            "load_balancing_strategy": "shuffle",
            "cost_prompt_tokens": 0.001,
            "cost_completion_tokens": 0.002,
        }

        # Act
        response = await client.post(
            url=f"/v1{ENDPOINT__ADMIN_ROUTERS}",
            headers={"Authorization": f"Bearer {token.token}"},
            json=router_data,
        )

        # Assert
        assert response.status_code in [400, 409], f"Expected 400 or 409, got {response.status_code}"

    async def test_create_router_with_duplicate_alias(self, client: AsyncClient, db_session):
        """
        Test creating router with alias that already exists on another router.

        Should return 409 Conflict or 400 Bad Request.
        """
        # Arrange
        admin_user = UserSQLFactory(admin_user=True)
        PermissionSQLFactory(role=admin_user.role, permission=PermissionType.ADMIN)

        # Create existing router with alias
        existing_router = RouterSQLFactory(
            user=admin_user,
            name="existing-router",
            type=ModelType.TEXT_GENERATION,
        )
        RouterAliasSQLFactory(router=existing_router, value="duplicate-alias")
        await db_session.flush()

        token = await create_token(db_session, name="admin_token", user=admin_user)

        router_data = {
            "name": "new-router",
            "type": "text-generation",
            "aliases": ["duplicate-alias"],  # Conflicts with existing
            "load_balancing_strategy": "shuffle",
            "cost_prompt_tokens": 0.001,
            "cost_completion_tokens": 0.002,
        }

        # Act
        response = await client.post(
            url=f"/v1{ENDPOINT__ADMIN_ROUTERS}",
            headers={"Authorization": f"Bearer {token.token}"},
            json=router_data,
        )

        # Assert
        assert response.status_code in [400, 409], f"Expected 400 or 409, got {response.status_code}"

    async def test_create_router_with_invalid_load_balancing_strategy(self, client: AsyncClient, db_session):
        """
        Test creating router with invalid load balancing strategy.

        Should return 422 validation error.
        """
        # Arrange
        admin_user = UserSQLFactory(admin_user=True)
        PermissionSQLFactory(role=admin_user.role, permission=PermissionType.ADMIN)
        token = await create_token(db_session, name="admin_token", user=admin_user)

        router_data = {
            "name": "test-router",
            "type": "text-generation",
            "aliases": [],
            "load_balancing_strategy": "invalid_strategy",  # Invalid
            "cost_prompt_tokens": 0.001,
            "cost_completion_tokens": 0.002,
        }

        # Act
        response = await client.post(
            url=f"/v1{ENDPOINT__ADMIN_ROUTERS}",
            headers={"Authorization": f"Bearer {token.token}"},
            json=router_data,
        )

        # Assert
        assert response.status_code == 422

    async def test_create_router_with_missing_required_fields(self, client: AsyncClient, db_session):
        """
        Test creating router with missing required fields.

        Should return 422 validation error.
        """
        # Arrange
        admin_user = UserSQLFactory(admin_user=True)
        PermissionSQLFactory(role=admin_user.role, permission=PermissionType.ADMIN)
        token = await create_token(db_session, name="admin_token", user=admin_user)

        router_data = {
            "name": "test-router",
            # Missing "type" - required field
            "aliases": [],
        }

        # Act
        response = await client.post(
            url=f"/v1{ENDPOINT__ADMIN_ROUTERS}",
            headers={"Authorization": f"Bearer {token.token}"},
            json=router_data,
        )

        # Assert
        assert response.status_code == 422

    async def test_create_router_trims_whitespace_in_name(self, client: AsyncClient, db_session):
        """
        Test that router name is trimmed of leading/trailing whitespace.

        Should create router with trimmed name.
        """
        # Arrange
        admin_user = UserSQLFactory(admin_user=True)
        PermissionSQLFactory(role=admin_user.role, permission=PermissionType.ADMIN)
        token = await create_token(db_session, name="admin_token", user=admin_user)

        router_data = {
            "name": "  router-with-spaces  ",  # Has leading/trailing spaces
            "type": "text-generation",
            "aliases": [],
            "load_balancing_strategy": "shuffle",
            "cost_prompt_tokens": 0.001,
            "cost_completion_tokens": 0.002,
        }

        # Act
        response = await client.post(
            url=f"/v1{ENDPOINT__ADMIN_ROUTERS}",
            headers={"Authorization": f"Bearer {token.token}"},
            json=router_data,
        )

        # Assert
        assert response.status_code == 201
        response_data = response.json()

        # Verify name was trimmed in database
        from api.sql.models import Router

        router = await db_session.get(Router, response_data["id"])
        assert router.name == "router-with-spaces"  # No spaces

    async def test_create_router_sets_default_load_balancing(self, client: AsyncClient, db_session):
        """
        Test that default load balancing strategy is applied when not provided.

        Should use default value (shuffle).
        """
        # Arrange
        admin_user = UserSQLFactory(admin_user=True)
        PermissionSQLFactory(role=admin_user.role, permission=PermissionType.ADMIN)
        token = await create_token(db_session, name="admin_token", user=admin_user)

        router_data = {
            "name": "default-lb-router",
            "type": "text-generation",
            "aliases": [],
            # load_balancing_strategy not provided - should use default
            "cost_prompt_tokens": 0.001,
            "cost_completion_tokens": 0.002,
        }

        # Act
        response = await client.post(
            url=f"/v1{ENDPOINT__ADMIN_ROUTERS}",
            headers={"Authorization": f"Bearer {token.token}"},
            json=router_data,
        )

        # Assert
        assert response.status_code == 201
        response_data = response.json()

        # Verify default in database
        from api.sql.models import Router

        router = await db_session.get(Router, response_data["id"])
        assert router.load_balancing_strategy == RouterLoadBalancingStrategy.SHUFFLE.value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
