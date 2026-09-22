from datetime import UTC, datetime, timedelta

from api.domain.key.entities import Key
from api.tests.unit.use_case.factories import KeyFactory


class TestKeyIsValid:
    def test_should_return_true_when_key_matches_and_is_usable(self):
        stored = KeyFactory(user_id=1, expires=None, revoked=False)
        decoded = Key.build_from_claims({"token_id": stored.id, "user_id": 1, "expires": None})

        assert decoded.is_valid(expected_key=stored) is True

    def test_should_return_false_when_stored_key_is_revoked(self):
        stored = KeyFactory(user_id=1, expires=None, revoked=True)
        decoded = Key.build_from_claims({"token_id": stored.id, "user_id": 1, "expires": None})

        assert decoded.is_valid(expected_key=stored) is False

    def test_should_return_false_when_stored_key_is_expired(self):
        stored = KeyFactory(user_id=1, expires=datetime.now(tz=UTC) - timedelta(days=1), revoked=False)
        decoded = Key.build_from_claims({"token_id": stored.id, "user_id": 1, "expires": None})

        assert decoded.is_valid(expected_key=stored) is False

    def test_should_return_false_when_user_id_does_not_match(self):
        stored = KeyFactory(user_id=1, expires=None, revoked=False)
        decoded = Key.build_from_claims({"token_id": stored.id, "user_id": 99, "expires": None})

        assert decoded.is_valid(expected_key=stored) is False


class TestKeyWithRevoked:
    def test_should_return_copy_with_revoked_flag(self):
        key = KeyFactory(revoked=False)

        updated = key.with_revoked(True)

        assert updated.revoked is True
        assert key.revoked is False
