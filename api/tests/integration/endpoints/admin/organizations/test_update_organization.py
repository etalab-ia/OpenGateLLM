from unittest.mock import create_autospec

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import _get_organization_authorization, update_organization_use_case_factory
from api.domain.organization import OrganizationAuthorization
from api.domain.organization.errors import (
    OrganizationAlreadyExistsError,
    OrganizationNotFoundError,
    UserCannotUpdateOrganizationError,
)
from api.infrastructure.fastapi.routes import EndpointRoute
from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.factories.sql import OrganizationSQLFactory, UserSQLFactory
from api.use_cases.admin.organizations import UpdateOrganizationUseCase

URL = f"/v1{EndpointRoute.ADMIN_ORGANIZATIONS}"


@pytest.mark.asyncio(loop_scope="session")
class TestUpdateOrganization:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.admin_user = UserSQLFactory(admin_user=True)
        self.key = await create_key(db_session, name="admin_key", user=self.admin_user)

    async def test_should_return_the_renamed_organization_when_the_user_is_authorized(self, client: AsyncClient, app, db_session):
        mock_organization_authorization = create_autospec(OrganizationAuthorization, instance=True, spec_set=True)
        mock_organization_authorization.can_update_organization.return_value = True
        app.dependency_overrides[_get_organization_authorization] = lambda: mock_organization_authorization
        organization = OrganizationSQLFactory(name="to-rename")
        await db_session.flush()

        response = await client.patch(
            url=f"{URL}/{organization.id}",
            headers={"Authorization": f"Bearer {self.key.token}"},
            json={"name": "renamed"},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["object"] == "organization"
        assert data["id"] == organization.id
        assert data["name"] == "renamed"

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (
                OrganizationNotFoundError(id=999),
                404,
                "Organization 999 not found.",
            ),
            (
                OrganizationAlreadyExistsError(name="already-taken"),
                409,
                "Organization already-taken already exists.",
            ),
            (
                UserCannotUpdateOrganizationError(user_id=7),
                403,
                "User 7 is not allowed to perform this action.",
            ),
        ],
    )
    async def test_should_map_each_domain_error_to_its_http_status(self, client: AsyncClient, app, use_case_result, expected_status, expected_detail):
        mock_use_case = create_autospec(UpdateOrganizationUseCase, instance=True, spec_set=True)
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[update_organization_use_case_factory] = lambda: mock_use_case

        response = await client.patch(
            url=f"{URL}/999",
            headers={"Authorization": f"Bearer {self.key.token}"},
            json={"name": "whatever"},
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
    async def test_should_return_401_when_the_request_is_not_authenticated(self, client: AsyncClient, headers, expected_status, expected_detail):
        response = await client.patch(url=f"{URL}/1", headers=headers, json={"name": "renamed"})

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
