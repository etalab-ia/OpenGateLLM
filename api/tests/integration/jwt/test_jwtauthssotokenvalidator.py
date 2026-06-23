from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ecdsa import NIST256p, SigningKey
from jose import JWTError, jwk, jwt
import pytest
import rsa

from api.domain.auth.errors import InvalidOidcTokenError
from api.infrastructure.jwt import JwtAuthSsoTokenValidator


@dataclass(frozen=True)
class RsaTestKey:
    signing_key: object
    public_jwk: dict


@dataclass(frozen=True)
class EcTestKey:
    signing_key: object
    public_jwk: dict


@pytest.fixture(scope="module")
def rsa_test_key() -> RsaTestKey:
    _, private_key = rsa.newkeys(2048)
    signing_key = jwk.construct(private_key.save_pkcs1().decode(), algorithm="RS256")
    public_jwk = signing_key.public_key().to_dict()
    public_jwk.update({"kid": "rsa-test-kid", "use": "sig", "alg": "RS256"})
    return RsaTestKey(signing_key=signing_key, public_jwk=public_jwk)


@pytest.fixture(scope="module")
def ec_test_key() -> EcTestKey:
    signing_key = jwk.construct(SigningKey.generate(curve=NIST256p).to_pem().decode(), algorithm="ES256")
    public_jwk = signing_key.public_key().to_dict()
    public_jwk.update({"kid": "ec-test-kid", "use": "sig", "alg": "ES256"})
    return EcTestKey(signing_key=signing_key, public_jwk=public_jwk)


@pytest.fixture
def validator() -> JwtAuthSsoTokenValidator:
    return JwtAuthSsoTokenValidator()


@pytest.fixture
def client_id() -> str:
    return "test-client-id"


def _encode_rs256_token(
    rsa_test_key: RsaTestKey,
    *,
    client_id: str,
    kid: str | None = "rsa-test-kid",
    expires_at: datetime | None = None,
) -> str:
    if expires_at is None:
        expires_at = datetime.now(tz=UTC) + timedelta(hours=1)

    headers = {"kid": kid} if kid is not None else None
    return jwt.encode(
        claims={"sub": "user-123", "aud": client_id, "exp": int(expires_at.timestamp())},
        key=rsa_test_key.signing_key,
        algorithm="RS256",
        headers=headers,
    )


def _encode_es256_token(
    ec_test_key: EcTestKey,
    *,
    client_id: str,
    expires_at: datetime | None = None,
) -> str:
    if expires_at is None:
        expires_at = datetime.now(tz=UTC) + timedelta(hours=1)

    return jwt.encode(
        claims={"sub": "user-456", "aud": client_id, "exp": int(expires_at.timestamp())},
        key=ec_test_key.signing_key,
        algorithm="ES256",
        headers={"kid": "ec-test-kid"},
    )


@pytest.mark.asyncio(loop_scope="session")
class TestJwtAuthSsoTokenValidator:
    async def test_validate_token_returns_claims_for_valid_rs256_token(
        self,
        validator: JwtAuthSsoTokenValidator,
        rsa_test_key: RsaTestKey,
        client_id: str,
    ):
        # Arrange
        token = _encode_rs256_token(rsa_test_key, client_id=client_id)
        jwks = {"keys": [rsa_test_key.public_jwk]}

        # Act
        result = await validator.validate_token(token=token, client_id=client_id, jwks=jwks)

        # Assert
        assert isinstance(result, dict)
        assert result["sub"] == "user-123"
        assert result["aud"] == client_id

    async def test_validate_token_returns_claims_for_valid_es256_token(
        self,
        validator: JwtAuthSsoTokenValidator,
        ec_test_key: EcTestKey,
        client_id: str,
    ):
        # Arrange
        token = _encode_es256_token(ec_test_key, client_id=client_id)
        jwks = {"keys": [ec_test_key.public_jwk]}

        # Act
        result = await validator.validate_token(token=token, client_id=client_id, jwks=jwks)

        # Assert
        assert isinstance(result, dict)
        assert result["sub"] == "user-456"
        assert result["aud"] == client_id

    async def test_validate_token_returns_error_when_kid_missing(
        self,
        validator: JwtAuthSsoTokenValidator,
        rsa_test_key: RsaTestKey,
        client_id: str,
    ):
        # Arrange
        token = _encode_rs256_token(rsa_test_key, client_id=client_id, kid=None)
        jwks = {"keys": [rsa_test_key.public_jwk]}

        # Act
        result = await validator.validate_token(token=token, client_id=client_id, jwks=jwks)

        # Assert
        assert result == InvalidOidcTokenError(message="No 'kid' found in JWT header")

    async def test_validate_token_returns_stale_jwks_error_when_kid_not_in_jwks(
        self,
        validator: JwtAuthSsoTokenValidator,
        rsa_test_key: RsaTestKey,
        client_id: str,
    ):
        # Arrange
        token = _encode_rs256_token(rsa_test_key, client_id=client_id)
        other_jwk = dict(rsa_test_key.public_jwk)
        other_jwk["kid"] = "other-kid"
        jwks = {"keys": [other_jwk]}

        # Act
        result = await validator.validate_token(token=token, client_id=client_id, jwks=jwks)

        # Assert
        assert result == InvalidOidcTokenError(
            message="No matching key found for kid: rsa-test-kid",
            stale_jwks=True,
        )

    async def test_validate_token_returns_error_when_audience_mismatch(
        self,
        validator: JwtAuthSsoTokenValidator,
        rsa_test_key: RsaTestKey,
        client_id: str,
    ):
        # Arrange
        token = _encode_rs256_token(rsa_test_key, client_id=client_id)
        jwks = {"keys": [rsa_test_key.public_jwk]}

        # Act
        result = await validator.validate_token(token=token, client_id="other-client-id", jwks=jwks)

        # Assert
        assert isinstance(result, InvalidOidcTokenError)
        assert result.stale_jwks is False
        assert "Invalid audience" in result.message

    async def test_validate_token_returns_error_when_token_expired(
        self,
        validator: JwtAuthSsoTokenValidator,
        rsa_test_key: RsaTestKey,
        client_id: str,
    ):
        # Arrange
        token = _encode_rs256_token(rsa_test_key, client_id=client_id, expires_at=datetime.now(tz=UTC) - timedelta(hours=1))
        jwks = {"keys": [rsa_test_key.public_jwk]}

        # Act
        result = await validator.validate_token(token=token, client_id=client_id, jwks=jwks)

        # Assert
        assert isinstance(result, InvalidOidcTokenError)
        assert result.stale_jwks is False
        assert "expired" in result.message

    async def test_validate_token_returns_error_when_signature_invalid(
        self,
        validator: JwtAuthSsoTokenValidator,
        rsa_test_key: RsaTestKey,
        client_id: str,
    ):
        # Arrange
        token = _encode_rs256_token(rsa_test_key, client_id=client_id)
        tampered_token = f"{token[:-5]}xxxxx"
        jwks = {"keys": [rsa_test_key.public_jwk]}

        # Act
        result = await validator.validate_token(token=tampered_token, client_id=client_id, jwks=jwks)

        # Assert
        assert isinstance(result, InvalidOidcTokenError)
        assert result.stale_jwks is False
        assert "Signature verification failed" in result.message

    async def test_validate_token_raises_when_token_is_malformed(
        self,
        validator: JwtAuthSsoTokenValidator,
        client_id: str,
    ):
        # Act / Assert
        with pytest.raises(JWTError):
            await validator.validate_token(token="not-a-valid-jwt", client_id=client_id, jwks={"keys": []})
