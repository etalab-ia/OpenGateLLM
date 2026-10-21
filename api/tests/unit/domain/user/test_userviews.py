from datetime import UTC, datetime, timedelta

from api.domain.role.entities import Limit, LimitType
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


class TestAuthenticatedUserViewLimitsFor:
    def test_should_keep_only_the_limits_of_the_router(self):
        # Arrange
        router_limit = Limit(router_id=1, type=LimitType.RPM, value=10)
        user = AuthenticatedUserFactory(limits=[router_limit, Limit(router_id=2, type=LimitType.RPM, value=20)])

        # Act & Assert
        assert user.limits_for(router_id=1) == [router_limit]
