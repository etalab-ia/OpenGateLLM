from datetime import UTC, datetime
import re

from api.domain.role.entities import LimitType
from api.domain.router.entities import RouterRateLimitState, RpdRateLimitState, RpmRateLimitState, TpdRateLimitState, TpmRateLimitState


class TestRouterRateLimitStateExceededLimits:
    @staticmethod
    def _state_with_tpm(remaining: int) -> RouterRateLimitState:
        # start with admin state - no limits
        state = RouterRateLimitState.admin_rate_limit_state()
        # set user's TPM limits to 100, and remaining to arg value
        state.tpm = TpmRateLimitState(value=100, remaining=remaining)
        return state

    @staticmethod
    def _state_with_tpd(remaining: int) -> RouterRateLimitState:
        state = RouterRateLimitState.admin_rate_limit_state()
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
        state = RouterRateLimitState.admin_rate_limit_state()

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
        state = RouterRateLimitState.admin_rate_limit_state()
        state.rpm = RpmRateLimitState(value=10, remaining=5, reset=0)
        state.rpd = RpdRateLimitState(value=1_000, remaining=500, reset=0)

        # Act
        headers = state.build_limit_headers(prompt_tokens=0)

        # Assert
        assert headers["x-ratelimit-limit-requests"] == "10"
        assert headers["x-ratelimit-remaining-requests"] == "4"

    def test_should_report_the_tokens_window_with_the_lowest_remaining(self):
        # Arrange
        state = RouterRateLimitState.admin_rate_limit_state()
        state.tpm = TpmRateLimitState(value=100, remaining=50, reset=0)
        state.tpd = TpdRateLimitState(value=1_000, remaining=500, reset=0)

        # Act
        headers = state.build_limit_headers(prompt_tokens=10)

        # Assert
        assert headers["x-ratelimit-limit-tokens"] == "100"
        assert headers["x-ratelimit-remaining-tokens"] == "40"

    def test_should_subtract_the_current_request_and_the_prompt_tokens_from_remaining(self):
        # Arrange
        state = RouterRateLimitState.admin_rate_limit_state()
        state.rpm = RpmRateLimitState(value=10, remaining=10, reset=0)
        state.tpm = TpmRateLimitState(value=100, remaining=100, reset=0)

        # Act
        headers = state.build_limit_headers(prompt_tokens=10)

        # Assert
        assert headers["x-ratelimit-remaining-requests"] == "9"
        assert headers["x-ratelimit-remaining-tokens"] == "90"

    def test_should_not_subtract_the_current_request_when_it_is_not_charged(self):
        # Arrange
        state = RouterRateLimitState.admin_rate_limit_state()
        state.rpm = RpmRateLimitState(value=10, remaining=5, reset=0)
        state.tpm = TpmRateLimitState(value=100, remaining=50, reset=0)

        # Act
        headers = state.build_limit_headers(prompt_tokens=100, charged=False)

        # Assert
        assert headers["x-ratelimit-remaining-requests"] == "5"
        assert headers["x-ratelimit-remaining-tokens"] == "50"

    def test_should_floor_remaining_at_zero(self):
        # Arrange
        state = RouterRateLimitState.admin_rate_limit_state()
        state.rpm = RpmRateLimitState(value=10, remaining=0, reset=0)

        # Act
        headers = state.build_limit_headers(prompt_tokens=0)

        # Assert
        assert headers["x-ratelimit-remaining-requests"] == "0"

    def test_should_report_the_full_period_as_reset_when_the_window_has_not_started(self):
        # Arrange
        state = RouterRateLimitState.admin_rate_limit_state()
        state.rpm = RpmRateLimitState(value=10, remaining=10, reset=0)
        state.tpd = TpdRateLimitState(value=1_000, remaining=1_000, reset=0)

        # Act
        headers = state.build_limit_headers(prompt_tokens=0)

        # Assert
        assert headers["x-ratelimit-reset-requests"] == "1m0s"
        assert headers["x-ratelimit-reset-tokens"] == "24h0m0s"

    def test_should_not_fall_back_to_the_period_when_the_reset_is_merely_in_the_past(self):
        # Arrange
        state = RouterRateLimitState.admin_rate_limit_state()
        state.rpm = RpmRateLimitState(value=10, remaining=10, reset=int(datetime.now(UTC).timestamp()))

        # Act
        headers = state.build_limit_headers(prompt_tokens=0)

        # Assert
        assert headers["x-ratelimit-reset-requests"] == "0s"

    def test_should_report_seconds_until_reset_when_the_window_has_started(self):
        # Arrange
        state = RouterRateLimitState.admin_rate_limit_state()
        state.rpm = RpmRateLimitState(value=10, remaining=10, reset=int(datetime.now(UTC).timestamp()) + 3_600)

        # Act
        headers = state.build_limit_headers(prompt_tokens=0)

        # Assert
        assert 3_598 <= self._duration_to_seconds(headers["x-ratelimit-reset-requests"]) <= 3_600

    def test_should_only_report_the_families_with_a_configured_limit(self):
        # Arrange
        state = RouterRateLimitState.admin_rate_limit_state()
        state.rpm = RpmRateLimitState(value=10, remaining=10, reset=0)

        # Act
        headers = state.build_limit_headers(prompt_tokens=0)

        # Assert
        assert set(headers) == {"x-ratelimit-limit-requests", "x-ratelimit-remaining-requests", "x-ratelimit-reset-requests"}

    def test_should_report_no_headers_when_no_limit_is_configured(self):
        # Arrange
        state = RouterRateLimitState.admin_rate_limit_state()

        # Act
        headers = state.build_limit_headers(prompt_tokens=10)

        # Assert
        assert headers == {}
