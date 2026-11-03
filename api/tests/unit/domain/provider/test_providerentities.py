from api.domain.provider.entities import ProviderEndpoint, ProviderLoads, ProviderRequest, ProviderResponse
from api.domain.rerank.entities import Rerank
from api.domain.usage.entities import Usage
from api.tests.unit.use_case.factories import ProviderFactory


class TestProviderQoSLimit:
    def test_should_replace_qos_limit(self):
        provider = ProviderFactory(qos_limit=None)

        updated_provider = provider.with_qos_limit(4)

        assert updated_provider.qos_limit == 4
        assert provider.qos_limit is None


class TestProviderLoads:
    def test_should_put_the_lowest_load_first_when_a_provider_has_no_limit(self):
        provider_with_limit = ProviderFactory(id=1, qos_limit=20)
        provider_without_limit = ProviderFactory(id=2, qos_limit=None)
        loads = ProviderLoads(load_by_provider_id={1: 3, 2: 5})

        sorted_providers = loads.sort_least_loaded_first([provider_without_limit, provider_with_limit])

        assert sorted_providers == [provider_with_limit, provider_without_limit]

    def test_should_put_the_most_remaining_capacity_first_when_every_provider_has_a_limit(self):
        least_loaded_provider = ProviderFactory(id=1, qos_limit=4)
        provider_with_most_remaining_capacity = ProviderFactory(id=2, qos_limit=10)
        loads = ProviderLoads(load_by_provider_id={1: 1, 2: 5})

        sorted_providers = loads.sort_least_loaded_first([least_loaded_provider, provider_with_most_remaining_capacity])

        assert sorted_providers == [provider_with_most_remaining_capacity, least_loaded_provider]

    def test_should_put_the_smallest_provider_id_first_when_loads_are_equal(self):
        first_provider = ProviderFactory(id=1)
        second_provider = ProviderFactory(id=2)
        loads = ProviderLoads(load_by_provider_id={1: 2, 2: 2})

        sorted_providers = loads.sort_least_loaded_first([second_provider, first_provider])

        assert sorted_providers == [first_provider, second_provider]


class TestProviderRequest:
    def test_should_generate_request_id_when_omitted(self):
        request = ProviderRequest(endpoint=ProviderEndpoint.MODELS)

        assert len(request.id) == 32
        assert request.id != ProviderRequest(endpoint=ProviderEndpoint.MODELS).id

    def test_should_keep_explicit_request_id(self):
        request = ProviderRequest(endpoint=ProviderEndpoint.MODELS, id="req-1")

        assert request.id == "req-1"


class TestProviderResponse:
    def test_should_return_the_usage_the_provider_reported(self):
        response = ProviderResponse(
            data=Rerank.model_validate({"id": "rerank-1", "model": "rerank-router", "results": [], "usage": {"prompt_tokens": 7, "total_tokens": 7}})
        )

        assert response.get_usage().prompt_tokens == 7

    def test_should_return_no_usage_when_the_provider_reported_none(self):
        response = ProviderResponse(data=Rerank.model_validate({"id": "rerank-1", "model": "rerank-router", "results": []}))

        assert response.data.usage.prompt_tokens == 0, "the field still holds its zero default"
        assert response.get_usage() is None

    def test_should_return_no_usage_for_a_text_response(self):
        assert ProviderResponse(text="a transcription").get_usage() is None

    def test_should_replace_the_provider_usage_without_changing_the_original_response(self):
        response = ProviderResponse(
            data=Rerank.model_validate({"id": "rerank-1", "model": "rerank-router", "results": [], "usage": {"prompt_tokens": 7, "total_tokens": 7}})
        )

        enriched = response.with_usage(Usage(prompt_tokens=7, total_tokens=7, cost=0.5))

        assert enriched.data.usage.cost == 0.5
        assert response.data.usage.cost == 0.0

    def test_should_leave_a_text_response_unchanged(self):
        response = ProviderResponse(text="a transcription")

        assert response.with_usage(Usage(cost=0.5)) is response
