import pytest


@pytest.fixture(scope="session")
def test_redis_pool():
    yield


@pytest.fixture(scope="session")
def test_configuration():
    from api.schemas.core.configuration import Configuration, Dependencies, Settings

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


@pytest.fixture(scope="function", autouse=True)
def _reset_redis_between_tests():
    yield
