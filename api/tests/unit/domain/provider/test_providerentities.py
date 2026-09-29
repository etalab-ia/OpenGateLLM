from unittest.mock import patch

import pytest

from api.domain.provider import ProviderAdmissionFull
from api.domain.provider.entities import ProviderEndpoint, ProviderRequest, ProviderResponse
from api.domain.rerank.entities import Rerank
from api.domain.usage.entities import Usage
from api.tests.unit.use_case.factories import ProviderFactory


class TestProviderAdmissionFull:
    @pytest.mark.parametrize("retries", [None, 0])
    def test_should_return_one_second_when_retry_window_is_empty(self, retries):
        assert ProviderAdmissionFull(depth=4).retry_after(retries=retries) == 1

    def test_should_scale_retry_after_with_depth(self):
        with patch("api.domain.provider._providerqos.random.random", return_value=0.5):
            assert ProviderAdmissionFull(depth=2).retry_after(retries=10) == 3

    def test_should_clamp_retry_after_to_retry_window(self):
        with patch("api.domain.provider._providerqos.random.random", return_value=0.99):
            assert ProviderAdmissionFull(depth=100).retry_after(retries=4) == 2


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
