from httpx import AsyncClient
import pytest

from api.tests.helpers import create_token
from api.tests.integration.factories import UserFactory
from api.utils.variables import ENDPOINT__MODELS


@pytest.mark.asyncio(loop_scope="session")
class TestModels:
    async def test_get_models_response_status_code(self, client: AsyncClient, db_session):
        """Test the GET /models response status code."""
        user1 = UserFactory(name="Alice", email="alice@example.com")
        user2 = UserFactory(name="Bob", email="bob@example.com")
        token2 = await create_token(db_session, name="my_token")

        response = await client.get(url=f"/v1{ENDPOINT__MODELS}", headers={"Authorization": f"Bearer {token2.token}"})
        assert response.status_code == 200, f"error: retrieve models ({response.status_code})"
