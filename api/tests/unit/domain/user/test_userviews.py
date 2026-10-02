from datetime import UTC, datetime, timedelta

from api.tests.unit.use_case.factories import AuthenticatedUserFactory


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
