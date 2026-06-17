from api.infrastructure.jwt import JwtKeyEncoder
from api.tests.integration.factories.sql import KeySQLFactory
from api.utils.configuration import configuration

INVALID_API_KEY = "sk-eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJ0b2tlbl9pZCI6OCwiZXhwaXJlcyI6MTc3OTMxMzE5NH0.jrigYbCVgAMhHLLEORa1fw-M9dtmZtRNNmsQDl3Fb10"


async def create_key(db_session, secret_key: str | None = None, **kwargs):
    """Create a key with a properly encoded API token value."""

    key = KeySQLFactory(**kwargs)
    await db_session.flush()

    secret_key = secret_key or configuration.settings.auth_secret_key
    key_encoder = JwtKeyEncoder(secret_key=secret_key)

    key.token = key_encoder.encode_token(user_id=key.user_id, key_id=key.id, expires=key.expires)

    await db_session.flush()

    return key
