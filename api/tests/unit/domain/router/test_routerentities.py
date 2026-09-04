from api.domain.role.entities import LimitType
from api.domain.router.entities import RouterRateLimitState, TpdRateLimitState, TpmRateLimitState
from api.tests.unit.use_case.factories import RouterFactory


class TestRouterIsBillable:
    def test_is_not_billable_when_both_costs_are_zero(self):
        # Arrange
        router = RouterFactory(free=True)

        # Act & Assert
        assert router.is_billable is False

    def test_is_billable_when_only_prompt_tokens_cost(self):
        # Arrange
        router = RouterFactory(cost_prompt_tokens=0.5, cost_completion_tokens=0.0)

        # Act & Assert
        assert router.is_billable is True

    def test_is_billable_when_only_completion_tokens_cost(self):
        # Arrange
        router = RouterFactory(cost_prompt_tokens=0.0, cost_completion_tokens=0.5)

        # Act & Assert
        assert router.is_billable is True

    def test_is_billable_when_both_costs_are_set(self):
        # Arrange
        router = RouterFactory(cost_prompt_tokens=0.5, cost_completion_tokens=0.5)

        # Act & Assert
        assert router.is_billable is True


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
