from jose import JWTError
import pytest

from api.helpers._identityaccessmanager import IdentityAccessManager


class TestPasswordEncryption:
    def test_hash_password_produces_bcrypt_hash(self):
        hashed = IdentityAccessManager._hash_password("mysecret")
        assert hashed.startswith("$2b$")

    def test_check_password_returns_true_for_correct_password(self):
        hashed = IdentityAccessManager._hash_password("mysecret")
        assert IdentityAccessManager._check_password("mysecret", hashed) is True

    def test_check_password_returns_false_for_wrong_password(self):
        hashed = IdentityAccessManager._hash_password("mysecret")
        assert IdentityAccessManager._check_password("wrongpassword", hashed) is False

    def test_password_hashes_are_unique_per_call(self):
        hash1 = IdentityAccessManager._hash_password("mysecret")
        hash2 = IdentityAccessManager._hash_password("mysecret")
        assert hash1 != hash2


class TestTokenEncryption:
    def test_encode_token_returns_sk_prefixed_string(self):
        iam = IdentityAccessManager(secret_key="test-secret")
        token = iam._encode_token(user_id=1, token_id=42)
        assert token.startswith("sk-")

    def test_encode_token_payload_contains_correct_claims(self):
        iam = IdentityAccessManager(secret_key="test-secret")
        token = iam._encode_token(user_id=7, token_id=99, expires=None)
        claims = iam._decode_token(token)
        assert claims["user_id"] == 7
        assert claims["token_id"] == 99
        assert claims["expires"] is None

    def test_decode_token_round_trip(self):
        iam = IdentityAccessManager(secret_key="my-secret-key")
        token = iam._encode_token(user_id=3, token_id=10, expires=9999999999)
        claims = iam._decode_token(token)
        assert claims["user_id"] == 3
        assert claims["token_id"] == 10
        assert claims["expires"] == 9999999999

    def test_decode_token_fails_with_wrong_secret_key(self):
        """Tokens encoded with key-a cannot be decoded with key-b (issue #716: key isolation)."""
        iam_a = IdentityAccessManager(secret_key="key-a")
        iam_b = IdentityAccessManager(secret_key="key-b")
        token = iam_a._encode_token(user_id=1, token_id=1)
        with pytest.raises(JWTError):
            iam_b._decode_token(token)

    def test_auth_master_key_as_raw_api_key_is_rejected(self):
        """The old auth_master_key was accepted as a raw API key.
        Since #716 it must be treated as an ordinary non-JWT string and rejected."""
        iam = IdentityAccessManager(secret_key="changeme")
        with pytest.raises(JWTError):
            iam._decode_token("sk-changeme")

    def test_changing_secret_key_invalidates_existing_tokens(self):
        """Rotating auth_secret_key must invalidate all previously issued tokens."""
        iam_old = IdentityAccessManager(secret_key="old-secret")
        iam_new = IdentityAccessManager(secret_key="new-secret")
        token = iam_old._encode_token(user_id=5, token_id=5)
        with pytest.raises(JWTError):
            iam_new._decode_token(token)
