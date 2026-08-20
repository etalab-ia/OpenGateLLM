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
