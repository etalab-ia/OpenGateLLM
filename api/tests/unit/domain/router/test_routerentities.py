from datetime import UTC, datetime
import re

import pytest

from api.domain import RouterType
from api.domain.model.errors import InconsistentModelMaxContextLengthError, InconsistentModelQosLimitError, InconsistentModelVectorSizeError
from api.domain.provider.entities import ProviderCapabilities, ProviderType
from api.domain.provider.errors import InvalidProviderTypeError
from api.domain.role.entities import LimitType
from api.domain.router.entities import RouterRateLimitState, RpdRateLimitState, RpmRateLimitState, TpdRateLimitState, TpmRateLimitState
from api.tests.unit.use_case.factories import ProviderFactory, RouterFactory


class TestRouterHasProviders:
    def test_should_be_true_when_the_router_has_one_provider(self):
        # Arrange
        router = RouterFactory(providers=[ProviderFactory()])

        # Act & Assert
        assert router.has_providers is True

    def test_should_be_false_when_the_router_has_no_provider(self):
        # Arrange
        router = RouterFactory(providers=[])

        # Act & Assert
        assert router.has_providers is False


class TestRouterIsCompatibleWithProviderType:
    @pytest.mark.parametrize(("router_type", "expected"), [(RouterType.TEXT_EMBEDDINGS_INFERENCE, True), (RouterType.TEXT_GENERATION, False)])
    def test_should_be_compatible_with_a_provider_type_only_when_the_router_type_allows_it(self, router_type, expected):
        # Arrange
        router = RouterFactory(type=router_type)

        # Act & Assert
        assert router.is_compatible_with_provider_type(ProviderType.TEI) is expected


class TestRouterCheckNewProvider:
    @pytest.fixture
    def router(self):
        return RouterFactory(id=1, name="my-router", providers=[ProviderFactory(vector_size=768, max_context_length=512, qos_limit=5)])

    def test_should_return_nothing_when_the_provider_is_consistent(self, router):
        # Act & Assert
        assert router.check_new_provider(ProviderCapabilities(vector_size=768, max_context_length=512), qos_limit=10) is None

    def test_should_return_inconsistent_vector_size_error_when_the_vector_sizes_differ(self, router):
        # Act
        result = router.check_new_provider(ProviderCapabilities(vector_size=384, max_context_length=512), qos_limit=10)

        # Assert
        assert result == InconsistentModelVectorSizeError(expected_vector_size=768, actual_vector_size=384, router_name="my-router")

    def test_should_return_inconsistent_max_context_length_error_when_the_max_context_lengths_differ(self, router):
        # Act
        result = router.check_new_provider(ProviderCapabilities(vector_size=768, max_context_length=1024), qos_limit=10)

        # Assert
        assert result == InconsistentModelMaxContextLengthError(
            expected_max_context_length=512, actual_max_context_length=1024, router_name="my-router"
        )

    def test_should_return_inconsistent_qos_limit_error_when_the_limit_mixes_open_providers_with_and_without_one(self, router):
        # Act
        result = router.check_new_provider(ProviderCapabilities(vector_size=768, max_context_length=512), qos_limit=None)

        # Assert
        assert result == InconsistentModelQosLimitError(router_id=1, router_name="my-router")


class TestRouterCheckProvider:
    def test_should_accept_removing_the_limit_of_the_only_provider_of_a_router(self):
        # Arrange
        provider = ProviderFactory(qos_limit=5)
        router = RouterFactory(providers=[provider])

        # Act & Assert
        assert router.check_provider(provider.with_qos_limit(None)) is None

    def test_should_return_inconsistent_qos_limit_error_when_the_limit_mixes_open_providers_with_and_without_one(self):
        # Arrange
        provider = ProviderFactory(qos_limit=5)
        router = RouterFactory(id=1, name="my-router", providers=[provider, ProviderFactory(qos_limit=5)])

        # Act & Assert
        assert router.check_provider(provider.with_qos_limit(None)) == InconsistentModelQosLimitError(router_id=1, router_name="my-router")

    def test_should_accept_a_closed_provider_in_a_mixed_router(self):
        # Arrange
        provider = ProviderFactory(qos_limit=5)
        router = RouterFactory(providers=[provider, ProviderFactory(qos_limit=5), ProviderFactory(qos_limit=None)])

        # Act & Assert
        assert router.check_provider(provider.with_qos_limit(0)) is None

    def test_should_return_invalid_provider_type_error_when_a_provider_of_an_incompatible_type_joins_the_router(self):
        # Arrange
        router = RouterFactory(type=RouterType.TEXT_GENERATION, providers=[])
        provider = ProviderFactory(type=ProviderType.TEI)

        # Act & Assert
        assert router.check_provider(provider) == InvalidProviderTypeError(
            provider_type=ProviderType.TEI.value, router_type=RouterType.TEXT_GENERATION.value
        )

    def test_should_check_the_capabilities_when_a_provider_joins_the_router(self):
        # Arrange
        router = RouterFactory(
            type=RouterType.TEXT_GENERATION, name="my-router", providers=[ProviderFactory(vector_size=None, max_context_length=512)]
        )
        provider = ProviderFactory(type=ProviderType.VLLM, vector_size=None, max_context_length=1024)

        # Act & Assert
        assert router.check_provider(provider) == InconsistentModelMaxContextLengthError(
            expected_max_context_length=512, actual_max_context_length=1024, router_name="my-router"
        )


class TestRouterEnforcesLimits:
    @pytest.mark.parametrize(("qos_retries_before_reject", "expected"), [(None, False), (0, True), (3, True)])
    def test_should_be_true_only_when_a_number_of_retries_is_set(self, qos_retries_before_reject, expected):
        # Arrange
        router = RouterFactory(qos_retries_before_reject=qos_retries_before_reject)

        # Act & Assert
        assert router.enforces_limits is expected


class TestRouterRateLimitStateExceededLimits:
    @staticmethod
    def _state_with_tpm(remaining: int) -> RouterRateLimitState:
        state = RouterRateLimitState.unlimited()
        state.tpm = TpmRateLimitState(value=100, remaining=remaining)
        return state

    @staticmethod
    def _state_with_tpd(remaining: int) -> RouterRateLimitState:
        state = RouterRateLimitState.unlimited()
        state.tpd = TpdRateLimitState(value=1_000, remaining=remaining)
        return state

    def test_should_report_tpm_when_the_prompt_is_larger_than_the_remaining_tokens(self):
        # Arrange
        state = self._state_with_tpm(remaining=9)

        # Act & Assert
        assert state.exceeded_limits(prompt_tokens=10) == [LimitType.TPM]

    def test_should_report_nothing_when_the_prompt_is_worth_exactly_the_remaining_tokens(self):
        # Arrange
        state = self._state_with_tpm(remaining=10)

        # Act & Assert
        assert state.exceeded_limits(prompt_tokens=10) == []

    def test_should_report_tpm_when_a_prompt_worth_no_token_meets_an_empty_window(self):
        # Arrange
        state = self._state_with_tpm(remaining=0)

        # Act & Assert
        assert state.exceeded_limits(prompt_tokens=0) == [LimitType.TPM]

    def test_should_report_tpd_when_the_prompt_is_larger_than_the_remaining_daily_tokens(self):
        # Arrange
        state = self._state_with_tpd(remaining=9)

        # Act & Assert
        assert state.exceeded_limits(prompt_tokens=10) == [LimitType.TPD]

    def test_should_report_nothing_when_no_limit_is_configured(self):
        # Arrange
        state = RouterRateLimitState.unlimited()

        # Act & Assert
        assert state.exceeded_limits(prompt_tokens=10_000) == []


class TestRouterRateLimitStateBuildLimitHeaders:
    @staticmethod
    def _duration_to_seconds(duration: str) -> int:
        hours = re.search(r"(\d+)h", duration)
        minutes = re.search(r"(\d+)m", duration)
        seconds = re.search(r"(\d+)s", duration)
        return (
            (int(hours.group(1)) if hours else 0) * 3600 + (int(minutes.group(1)) if minutes else 0) * 60 + (int(seconds.group(1)) if seconds else 0)
        )

    def test_should_report_the_requests_window_with_the_lowest_remaining(self):
        # Arrange
        state = RouterRateLimitState.unlimited()
        state.rpm = RpmRateLimitState(value=10, remaining=5, reset=0)
        state.rpd = RpdRateLimitState(value=1_000, remaining=500, reset=0)

        # Act
        headers = state.build_limit_headers(prompt_tokens=0)

        # Assert
        assert headers["x-ratelimit-limit-requests"] == "10"
        assert headers["x-ratelimit-remaining-requests"] == "4"

    def test_should_report_the_tokens_window_with_the_lowest_remaining(self):
        # Arrange
        state = RouterRateLimitState.unlimited()
        state.tpm = TpmRateLimitState(value=100, remaining=50, reset=0)
        state.tpd = TpdRateLimitState(value=1_000, remaining=500, reset=0)

        # Act
        headers = state.build_limit_headers(prompt_tokens=10)

        # Assert
        assert headers["x-ratelimit-limit-tokens"] == "100"
        assert headers["x-ratelimit-remaining-tokens"] == "40"

    def test_should_subtract_the_current_request_and_the_prompt_tokens_from_remaining(self):
        # Arrange
        state = RouterRateLimitState.unlimited()
        state.rpm = RpmRateLimitState(value=10, remaining=10, reset=0)
        state.tpm = TpmRateLimitState(value=100, remaining=100, reset=0)

        # Act
        headers = state.build_limit_headers(prompt_tokens=10)

        # Assert
        assert headers["x-ratelimit-remaining-requests"] == "9"
        assert headers["x-ratelimit-remaining-tokens"] == "90"

    def test_should_not_subtract_the_current_request_when_it_is_not_charged(self):
        # Arrange
        state = RouterRateLimitState.unlimited()
        state.rpm = RpmRateLimitState(value=10, remaining=5, reset=0)
        state.tpm = TpmRateLimitState(value=100, remaining=50, reset=0)

        # Act
        headers = state.build_limit_headers(prompt_tokens=100, charged=False)

        # Assert
        assert headers["x-ratelimit-remaining-requests"] == "5"
        assert headers["x-ratelimit-remaining-tokens"] == "50"

    def test_should_floor_remaining_at_zero(self):
        # Arrange
        state = RouterRateLimitState.unlimited()
        state.rpm = RpmRateLimitState(value=10, remaining=0, reset=0)

        # Act
        headers = state.build_limit_headers(prompt_tokens=0)

        # Assert
        assert headers["x-ratelimit-remaining-requests"] == "0"

    def test_should_report_the_full_period_as_reset_when_the_window_has_not_started(self):
        # Arrange
        state = RouterRateLimitState.unlimited()
        state.rpm = RpmRateLimitState(value=10, remaining=10, reset=0)
        state.tpd = TpdRateLimitState(value=1_000, remaining=1_000, reset=0)

        # Act
        headers = state.build_limit_headers(prompt_tokens=0)

        # Assert
        assert headers["x-ratelimit-reset-requests"] == "1m0s"
        assert headers["x-ratelimit-reset-tokens"] == "24h0m0s"

    def test_should_not_fall_back_to_the_period_when_the_reset_is_merely_in_the_past(self):
        # Arrange
        state = RouterRateLimitState.unlimited()
        state.rpm = RpmRateLimitState(value=10, remaining=10, reset=int(datetime.now(UTC).timestamp()))

        # Act
        headers = state.build_limit_headers(prompt_tokens=0)

        # Assert
        assert headers["x-ratelimit-reset-requests"] == "0s"

    def test_should_report_seconds_until_reset_when_the_window_has_started(self):
        # Arrange
        state = RouterRateLimitState.unlimited()
        state.rpm = RpmRateLimitState(value=10, remaining=10, reset=int(datetime.now(UTC).timestamp()) + 3_600)

        # Act
        headers = state.build_limit_headers(prompt_tokens=0)

        # Assert
        assert 3_598 <= self._duration_to_seconds(headers["x-ratelimit-reset-requests"]) <= 3_600

    def test_should_only_report_the_families_with_a_configured_limit(self):
        # Arrange
        state = RouterRateLimitState.unlimited()
        state.rpm = RpmRateLimitState(value=10, remaining=10, reset=0)

        # Act
        headers = state.build_limit_headers(prompt_tokens=0)

        # Assert
        assert set(headers) == {"x-ratelimit-limit-requests", "x-ratelimit-remaining-requests", "x-ratelimit-reset-requests"}

    def test_should_report_no_headers_when_no_limit_is_configured(self):
        # Arrange
        state = RouterRateLimitState.unlimited()

        # Act
        headers = state.build_limit_headers(prompt_tokens=10)

        # Assert
        assert headers == {}
