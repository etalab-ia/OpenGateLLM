import pytest

from api.utils.context import global_context
from api.helpers.models.routers._modelrouter import ModelRouter


@pytest.mark.usefixtures("client")
class TestModels:
    @pytest.mark.asyncio
    async def test_get_model_client(self):
        # Get a language model with more than 1 client
        router = await global_context.model_registry(model="albert-small")

        # With roundrobin client should be different at each call
        client_1, _ = router.get_client(endpoint="")
        client_2, _ = router.get_client(endpoint="")
        client_3, _ = router.get_client(endpoint="")

        assert client_1.timeout != client_2.timeout
        assert client_1.timeout == client_3.timeout

    @pytest.mark.asyncio
    async def test_router_cycle_offset_roundtrip(self):
        # Get a language model with more than 1 client
        router = await global_context.model_registry(model="albert-small")
        next(router._cycle)

        # Act: go to schema and back
        schema = await router.as_schema(censored=False)
        router_copy = ModelRouter.from_schema(schema)

        # Assert: offset preserved across round trip
        assert router._cycle.offset == 1
        assert router_copy._cycle.offset == 1
