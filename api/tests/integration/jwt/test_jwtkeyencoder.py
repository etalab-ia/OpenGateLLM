from datetime import UTC, datetime

from jwt import PyJWTError
import pytest

from api.domain.key import KeyEncoder
from api.infrastructure.jwt import JwtKeyEncoder
from api.tests.helpers import TEST_AUTH_SECRET_KEY


@pytest.fixture
def secret_key() -> str:
    return TEST_AUTH_SECRET_KEY


@pytest.fixture
def key_encoder(secret_key: str) -> JwtKeyEncoder:
    return JwtKeyEncoder(secret_key=secret_key)


class TestJwtKeyEncoder:
    def test_encode_token_returns_sk_prefixed_string(self, key_encoder: JwtKeyEncoder):
        # Act
        token = key_encoder.encode_token(user_id=1, key_id=42)

        # Assert
        assert token.startswith(KeyEncoder.KEY_PREFIX)

    def test_encode_token_payload_contains_correct_claims(self, key_encoder: JwtKeyEncoder):
        # Act
        token = key_encoder.encode_token(user_id=7, key_id=99, expires=None)
        claims = key_encoder.decode(key_value=token)

        # Assert
        assert claims["user_id"] == 7
        assert claims["token_id"] == 99
        assert claims["expires"] is None

    def test_encode_token_includes_expiration_timestamp(self, key_encoder: JwtKeyEncoder):
        # Arrange
        expires_at = datetime(2030, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Act
        token = key_encoder.encode_token(user_id=3, key_id=10, expires=expires_at)
        claims = key_encoder.decode(key_value=token)

        # Assert
        assert claims["user_id"] == 3
        assert claims["token_id"] == 10
        assert claims["expires"] == int(expires_at.timestamp())

    def test_decode_succeeds_when_key_contains_sk_string_after_prefix(self, key_encoder: JwtKeyEncoder):
        # Arrange
        token = key_encoder.encode_token(user_id=3, key_id=67)
        assert KeyEncoder.KEY_PREFIX in token.removeprefix(KeyEncoder.KEY_PREFIX)

        # Act
        claims = key_encoder.decode(key_value=token)

        # Assert
        assert claims["user_id"] == 3
        assert claims["token_id"] == 67

    def test_decode_accepts_a_key_issued_by_python_jose(self, key_encoder: JwtKeyEncoder):
        # Arrange
        # Issued by python-jose 3.5.0, the former implementation, with TEST_AUTH_SECRET_KEY: the keys already given to users must stay valid.
        key_issued_by_python_jose = (
            "sk-eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
            ".eyJ1c2VyX2lkIjoxMiwidG9rZW5faWQiOjM0LCJleHBpcmVzIjoxODkzNDU2MDAwfQ"
            ".xEbByVJ_XAy1UWQafWyKku2X_P3OZGn_WRDs-fSo4YQ"
        )

        # Act
        claims = key_encoder.decode(key_value=key_issued_by_python_jose)

        # Assert
        assert claims == {"user_id": 12, "token_id": 34, "expires": int(datetime(2030, 1, 1, tzinfo=UTC).timestamp())}

    def test_decode_fails_with_wrong_secret_key(self, secret_key: str):
        # Arrange
        encoder_a = JwtKeyEncoder(secret_key="secret-key-a-at-least-32-bytes-long")
        encoder_b = JwtKeyEncoder(secret_key="secret-key-b-at-least-32-bytes-long")
        token = encoder_a.encode_token(user_id=1, key_id=1)

        # Act / Assert
        with pytest.raises(PyJWTError):
            encoder_b.decode(key_value=token)

    def test_decode_fails_when_value_is_not_a_jwt(self, key_encoder: JwtKeyEncoder):
        # Act / Assert
        with pytest.raises(PyJWTError):
            key_encoder.decode(key_value="sk-not-a-valid-jwt")

    def test_changing_secret_key_invalidates_existing_tokens(self):
        # Arrange
        encoder_old = JwtKeyEncoder(secret_key="old-secret-key-at-least-32-bytes-long")
        encoder_new = JwtKeyEncoder(secret_key="new-secret-key-at-least-32-bytes-long")
        token = encoder_old.encode_token(user_id=5, key_id=5)

        # Act / Assert
        with pytest.raises(PyJWTError):
            encoder_new.decode(key_value=token)
