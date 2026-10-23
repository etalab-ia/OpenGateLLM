from api.domain.provider.entities import ProviderResponse
from api.domain.rerank.entities import Rerank
from api.domain.usage.entities import Usage


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
