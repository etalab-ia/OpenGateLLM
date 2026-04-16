import pytest_asyncio


@pytest_asyncio.fixture(scope="function", autouse=True)
async def _restore_dependency_overrides(app):
    snapshot = dict(app.dependency_overrides)
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(snapshot)
