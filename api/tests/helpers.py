from jose import jwt

from api.domain.key import KeyRepository
from api.tests.integration.factories.sql import KeySQLFactory
from api.utils.configuration import configuration

INVALID_API_KEY = "sk-eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJ0b2tlbl9pZCI6OCwiZXhwaXJlcyI6MTc3OTMxMzE5NH0.jrigYbCVgAMhHLLEORa1fw-M9dtmZtRNNmsQDl3Fb10"


async def create_key(db_session, secret_key: str | None = None, **kwargs):
    """Create a key with a properly encoded API token value."""

    key = KeySQLFactory(**kwargs)
    await db_session.flush()

    secret_key = secret_key or configuration.settings.auth_secret_key

    expires = int(key.expires.timestamp()) if key.expires is not None else None
    key.token = KeyRepository.TOKEN_PREFIX + jwt.encode(
        claims={"user_id": key.user_id, "token_id": key.id, "expires": expires},
        key=secret_key,
        algorithm="HS256",
    )

    await db_session.flush()

    return key
