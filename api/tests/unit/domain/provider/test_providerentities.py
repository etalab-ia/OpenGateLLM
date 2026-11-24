import random
from unittest.mock import create_autospec

import pytest

from api.domain.provider.entities import Provider, ProviderEndpoint, ProviderLoads, ProviderRequest, ProviderResponse
from api.domain.rerank.entities import Rerank
from api.domain.usage.entities import Usage
from api.tests.unit.use_case.factories import ProviderFactory


class TestProviderKey:
    def test_should_not_appear_in_the_representation(self):
        # Arrange
        provider = ProviderFactory(key="secret-key")

        # Act & Assert
        assert "secret-key" not in repr(provider)


class TestProviderQoSLimit:
    def test_should_replace_qos_limit(self):
        provider = ProviderFactory(qos_limit=None)

        updated_provider = provider.with_qos_limit(4)

        assert updated_provider.qos_limit == 4
        assert provider.qos_limit is None

    @pytest.mark.parametrize("qos_limits", [[5, None], [None, 5], [5, 10, None]])
    def test_should_mix_qos_limits_when_open_providers_have_and_lack_a_limit(self, qos_limits):
        assert Provider.mixes_qos_limits(qos_limits)

    @pytest.mark.parametrize("qos_limits", [[5, 10], [None, None], [5], [None], []])
    def test_should_not_mix_qos_limits_when_every_open_provider_is_of_the_same_mode(self, qos_limits):
        assert not Provider.mixes_qos_limits(qos_limits)

    @pytest.mark.parametrize("qos_limits", [[0, None], [0, 5], [5, 0, 10], [None, 0, None]])
    def test_should_not_mix_qos_limits_when_only_a_closed_provider_differs(self, qos_limits):
        assert not Provider.mixes_qos_limits(qos_limits)


class TestProviderLoads:
    @pytest.fixture
    def mock_random_generator(self):
        random_generator = create_autospec(random.Random, instance=True, spec_set=True)
        random_generator.random.return_value = 0.5
        return random_generator

    def test_should_put_the_lowest_load_rate_provider_first_when_the_other_one_has_more_free_slots(self, mock_random_generator):
        large_provider = ProviderFactory(id=1, qos_limit=100)
        small_provider = ProviderFactory(id=2, qos_limit=10)
        loads = ProviderLoads(load_by_provider_id={1: 80, 2: 0})

        sorted_providers = loads.sort_by_load_rate([large_provider, small_provider], mock_random_generator)

        assert sorted_providers == [small_provider, large_provider]

    def test_should_put_the_provider_with_more_free_slots_first_when_both_have_the_same_load_rate(self, mock_random_generator):
        small_provider = ProviderFactory(id=1, qos_limit=10)
        large_provider = ProviderFactory(id=2, qos_limit=100)
        loads = ProviderLoads(load_by_provider_id={1: 5, 2: 50})

        sorted_providers = loads.sort_by_load_rate([small_provider, large_provider], mock_random_generator)

        assert sorted_providers == [large_provider, small_provider]

    def test_should_put_the_provider_with_the_lowest_draw_first_when_both_have_the_same_load_rate_and_free_slots(self, mock_random_generator):
        other_provider = ProviderFactory(id=1, qos_limit=5)
        drawn_provider = ProviderFactory(id=2, qos_limit=5)
        loads = ProviderLoads(load_by_provider_id={1: 2, 2: 2})
        mock_random_generator.random.side_effect = [0.9, 0.1]

        sorted_providers = loads.sort_by_load_rate([other_provider, drawn_provider], mock_random_generator)

        assert sorted_providers == [drawn_provider, other_provider]

    def test_should_return_the_load_counted_for_the_provider(self):
        loads = ProviderLoads(load_by_provider_id={1: 3})

        assert loads.load_of(ProviderFactory(id=1)) == 3


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
