from jose import jwt

from api.helpers._identityaccessmanager import IdentityAccessManager
from api.tests.integration.factories.sql import TokenSQLFactory
from api.utils.configuration import configuration

INVALID_API_KEY = "sk-eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJ0b2tlbl9pZCI6OCwiZXhwaXJlcyI6MTc3OTMxMzE5NH0.jrigYbCVgAMhHLLEORa1fw-M9dtmZtRNNmsQDl3Fb10"


async def create_key(db_session, **kwargs):
    """Create a token with properly encoded string."""

    key = TokenSQLFactory(**kwargs)
    await db_session.flush()

    key.token = IdentityAccessManager.TOKEN_PREFIX + jwt.encode(
        claims={"user_id": key.user_id, "token_id": key.id, "expires": key.expires.isoformat() if key.expires else None},
        key=configuration.settings.auth_secret_key,
        algorithm="HS256",
    )

    await db_session.flush()

    return key
