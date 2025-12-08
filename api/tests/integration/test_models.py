from httpx import AsyncClient

from api.tests.helpers import create_token
from api.tests.integration.factories import UserFactory
from api.utils.variables import ENDPOINT__MODELS


class TestModels:
    async def test_get_models_response_status_code(self, client: AsyncClient, db_session):
        """Test the GET /models response status code."""
        user1 = UserFactory(name="Alice", email="alice@example.com")
        user2 = UserFactory(name="Bob", email="bob@example.com")
        # token = TokenFactory(name="api_token")
        token2 = await create_token(db_session, name="my_token")

        await db_session.commit()
        response = await client.get(url=f"/v1{ENDPOINT__MODELS}", headers={"Authorization": f"Bearer {token2.token}"})
        assert response.status_code == 200, f"error: retrieve models ({response.status_code})"

        # models = Models(data=[Model(**model) for model in response.json()["data"]])
        # assert isinstance(models, Models)
        # assert all(isinstance(model, Model) for model in models.data)
        #
        # model = models.data[0].id
        # response = client.get_without_permissions(url=f"/v1{ENDPOINT__MODELS}/{model}")
        # assert response.status_code == 200, f"error: retrieve model ({response.status_code})"
        #
        # model = Model(**response.json())
        # assert isinstance(model, Model)
