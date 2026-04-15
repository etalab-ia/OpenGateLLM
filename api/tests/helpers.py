from jose import jwt

from api.helpers._identityaccessmanager import IdentityAccessManager
from api.tests.integration.factories.sql import TokenSQLFactory
from api.utils.configuration import configuration


async def create_token(db_session, **kwargs):
    """Create a token with properly encoded string."""

    token = TokenSQLFactory(**kwargs)
    await db_session.flush()

    token.token = IdentityAccessManager.TOKEN_PREFIX + jwt.encode(
        claims={"user_id": token.user_id, "token_id": token.id, "expires": token.expires.isoformat() if token.expires else None},
        key=configuration.settings.auth_secret_key,
        algorithm="HS256",
    )

    await db_session.flush()

    return token
