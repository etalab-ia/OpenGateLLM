from datetime import UTC, datetime, timedelta

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


class TestAuthenticatedUserViewHasExpired:
    def test_has_not_expired_when_expires_is_none(self):
        # Arrange
        user = AuthenticatedUserFactory(no_expiration=True)

        # Act & Assert
        assert user.has_expired is False

    def test_has_not_expired_when_expires_is_in_the_future(self):
        # Arrange
        user = AuthenticatedUserFactory(expires=datetime.now(tz=UTC) + timedelta(days=1))

        # Act & Assert
        assert user.has_expired is False

    def test_has_expired_when_expires_is_in_the_past(self):
        # Arrange
        user = AuthenticatedUserFactory(expires=datetime.now(tz=UTC) - timedelta(days=1))

        # Act & Assert
        assert user.has_expired is True

    def test_naive_expires_is_read_as_utc(self):
        # Arrange
        user = AuthenticatedUserFactory(expires=datetime.now(tz=UTC).replace(tzinfo=None) - timedelta(days=1))

        # Act & Assert
        assert user.expires.tzinfo == UTC
        assert user.has_expired is True
