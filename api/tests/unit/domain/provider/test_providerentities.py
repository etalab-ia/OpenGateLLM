from api.domain.provider.entities import ProviderEndpoint, ProviderRequest
from api.tests.unit.use_case.factories import ProviderFactory


class TestProviderQoSLimit:
    def test_should_replace_qos_limit(self):
        provider = ProviderFactory(qos_limit=None)

        updated_provider = provider.with_qos_limit(4)

        assert updated_provider.qos_limit == 4
        assert provider.qos_limit is None


class TestProviderRequest:
    def test_should_generate_request_id_when_omitted(self):
        request = ProviderRequest(endpoint=ProviderEndpoint.MODELS)

        assert len(request.id) == 32
        assert request.id != ProviderRequest(endpoint=ProviderEndpoint.MODELS).id

    def test_should_keep_explicit_request_id(self):
        request = ProviderRequest(endpoint=ProviderEndpoint.MODELS, id="req-1")

        assert request.id == "req-1"
