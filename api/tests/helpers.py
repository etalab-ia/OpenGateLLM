from jose import jwt

from api.tests.integration.factories import TokenFactory
from api.utils.configuration import configuration


async def create_token(db_session, **kwargs):
    """Create a token with properly encoded string."""

    token = TokenFactory(**kwargs)
    await db_session.flush()

    token.token = "sk-" + jwt.encode(
        claims={"user_id": token.user_id, "token_id": token.id, "expires": token.expires.isoformat() if token.expires else None},
        key=configuration.settings.auth_master_key,
        algorithm="HS256",
    )

    await db_session.flush()
    # await db_session.refresh(token)

    return token
