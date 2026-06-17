from datetime import UTC, datetime

from jose import JWTError
import pytest

from api.domain.key import KeyEncoder
from api.infrastructure.jwt import JwtKeyEncoder


@pytest.fixture
def secret_key() -> str:
    return "MY_SECRET_KEY"


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

    def test_decode_fails_with_wrong_secret_key(self, secret_key: str):
        # Arrange
        encoder_a = JwtKeyEncoder(secret_key="key-a")
        encoder_b = JwtKeyEncoder(secret_key="key-b")
        token = encoder_a.encode_token(user_id=1, key_id=1)

        # Act / Assert
        with pytest.raises(JWTError):
            encoder_b.decode(key_value=token)

    def test_decode_fails_when_value_is_not_a_jwt(self, key_encoder: JwtKeyEncoder):
        # Act / Assert
        with pytest.raises(JWTError):
            key_encoder.decode(key_value="sk-not-a-valid-jwt")

    def test_changing_secret_key_invalidates_existing_tokens(self):
        # Arrange
        encoder_old = JwtKeyEncoder(secret_key="old-secret")
        encoder_new = JwtKeyEncoder(secret_key="new-secret")
        token = encoder_old.encode_token(user_id=5, key_id=5)

        # Act / Assert
        with pytest.raises(JWTError):
            encoder_new.decode(key_value=token)
