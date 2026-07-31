from api.tests.unit.use_case.factories import AuthenticatedUserFactory


class TestAuthenticatedUserViewHasInsufficientBudget:
    def test_has_insufficient_budget_when_budget_is_zero(self):
        # Arrange
        user = AuthenticatedUserFactory(budget=0)

        # Act & Assert
        assert user.has_insufficient_budget is True

    def test_has_sufficient_budget_when_budget_is_positive(self):
        # Arrange
        user = AuthenticatedUserFactory(budget=10.0)

        # Act & Assert
        assert user.has_insufficient_budget is False

    def test_has_sufficient_budget_when_budget_is_unlimited(self):
        # Arrange
        user = AuthenticatedUserFactory(unlimited_budget=True)

        # Act & Assert
        assert user.has_insufficient_budget is False
