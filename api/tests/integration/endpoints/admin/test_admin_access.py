from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.app import create_app
from api.schemas.core.configuration import Configuration, Dependencies, Settings
from api.tests.helpers import create_key
from api.tests.integration.endpoints.utils import NOT_ADMIN_USER_DETAIL, collect_admin_only_routes
from api.tests.integration.factories.sql import UserSQLFactory


def _test_configuration() -> Configuration:
    return Configuration.model_construct(
        settings=Settings.model_construct(
            app_title="test",
            swagger_summary=None,
            swagger_version="0.0.0",
            swagger_description=None,
            swagger_terms_of_service=None,
            swagger_contact=None,
            swagger_license_info=None,
            swagger_openapi_tags=[],
            swagger_docs_url=None,
            swagger_redoc_url=None,
            disabled_routers=[],
            hidden_routers=[],
            monitoring_prometheus_enabled=False,
        ),
        dependencies=Dependencies.model_construct(sentry=None),
    )


ADMIN_ONLY_ROUTES = collect_admin_only_routes(create_app(_test_configuration(), skip_lifespan=True))
assert ADMIN_ONLY_ROUTES, "Expected at least one admin-only route"


@pytest.mark.asyncio(loop_scope="session")
class TestAdminAccessController:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.non_admin_user = UserSQLFactory(regular_user=True)
        self.non_admin_key = await create_key(
            db_session,
            name="regular_user_key",
            user=self.non_admin_user,
            never_expires=True,
        )

    @pytest.mark.parametrize(
        "method,path",
        ADMIN_ONLY_ROUTES,
        ids=[f"{method} {path}" for method, path in ADMIN_ONLY_ROUTES],
    )
    async def test_admin_only_endpoints_reject_non_admin_user(self, client: AsyncClient, method: str, path: str):
        response = await client.request(
            method=method,
            url=path,
            headers={"Authorization": f"Bearer {self.non_admin_key.token}"},
            json={} if method in {"POST", "PATCH", "PUT"} else None,
        )

        assert response.status_code == 403, response.text
        assert response.json().get("detail") == NOT_ADMIN_USER_DETAIL
