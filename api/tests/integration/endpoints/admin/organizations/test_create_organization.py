from unittest.mock import AsyncMock, create_autospec

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import _get_organization_authorization, create_organization_use_case_factory
from api.domain.organization import OrganizationAuthorization
from api.domain.organization.errors import OrganizationAlreadyExistsError, UserCannotCreateOrganizationError
from api.infrastructure.fastapi.routes import EndpointRoute
from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.factories.sql import UserSQLFactory

URL = f"/v1{EndpointRoute.ADMIN_ORGANIZATIONS}"


def _valid_body(**overrides) -> dict:
    body = {"name": "new-organization"}
    body.update(overrides)
    return body


@pytest.mark.asyncio(loop_scope="session")
class TestCreateOrganization:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.admin_user = UserSQLFactory(admin_user=True)
        self.key = await create_key(db_session, name="admin_key", user=self.admin_user)

    @pytest.fixture
    def mock_organization_authorization(self, app):
        # No OpenFGA server in the tests: the port answers in its place.
        mock_authorization = create_autospec(OrganizationAuthorization, instance=True, spec_set=True)
        mock_authorization.can_create_organization.return_value = True
        app.dependency_overrides[_get_organization_authorization] = lambda: mock_authorization
        return mock_authorization

    async def test_should_return_the_organization_when_the_user_is_allowed_to_create_it(
        self, client: AsyncClient, db_session, mock_organization_authorization
    ):
        await db_session.flush()

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(),
        )

        assert response.status_code == 201, response.text
        data = response.json()
        assert data["object"] == "organization"
        assert data["name"] == "new-organization"
        assert isinstance(data["id"], int)
        assert data["users"] == 0
        assert isinstance(data["created"], int)
        assert isinstance(data["updated"], int)

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (
                OrganizationAlreadyExistsError(name="existing-organization"),
                409,
                "Organization existing-organization already exists.",
            ),
            (
                UserCannotCreateOrganizationError(user_id=7),
                403,
                "User 7 is not allowed to perform this action.",
            ),
        ],
    )
    async def test_should_map_each_domain_error_to_its_http_status(self, client: AsyncClient, app, use_case_result, expected_status, expected_detail):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[create_organization_use_case_factory] = lambda: mock_use_case

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(),
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
    async def test_should_reject_the_request_when_the_key_is_missing_or_invalid(self, client: AsyncClient, headers, expected_status, expected_detail):
        response = await client.post(url=URL, headers=headers, json=_valid_body())

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
