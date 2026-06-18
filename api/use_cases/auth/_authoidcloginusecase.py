from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import logging
import time
from typing import Any

import httpx
from jose import JWTError, jwk, jwt

from api.domain.auth.errors import InvalidOidcTokenError
from api.domain.key import KeyRepository
from api.domain.key.entities import Key
from api.domain.user import UserRepository
from api.utils.logging import init_logger  # noqa: F401 E402


@dataclass
class AuthOidcLoginCommand:
    email: str
    id_token: str


@dataclass
class AuthOidcLoginUseCaseSuccess:
    key: Key


type AuthOidcLoginUseCaseResult = AuthOidcLoginUseCaseSuccess | InvalidOidcTokenError


logger = logging.getLogger(__name__)

_discovery_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_jwks_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_CACHE_TTL_SECONDS = 3600


async def _cached_get(url: str, cache: dict[str, tuple[float, dict[str, Any]]]) -> dict[str, Any]:
    now = time.monotonic()
    cached = cache.get(url)
    if cached and now - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=10.0)
        response.raise_for_status()
        payload = response.json()

    cache[url] = (now, payload)
    return payload


async def get_jwks_keys(*, issuer_url: str) -> dict[str, Any] | None:
    """Retrieve JWKS from the OIDC provider discovery document."""
    try:
        metadata = await _cached_get(url=f"{issuer_url.rstrip('/')}/.well-known/openid-configuration", cache=_discovery_cache)
        jwks_uri = metadata.get("jwks_uri")
        if not jwks_uri:
            logger.warning("No jwks_uri found in OIDC server metadata")
            return None
        return await _cached_get(url=jwks_uri, cache=_jwks_cache)
    except Exception as exc:
        logger.error("Error fetching JWKS: %s", exc)
        return None


async def validate_oidc_id_token(
    id_token: str,
    *,
    issuer_url: str,
    client_id: str | None = None,
    access_token: str | None = None,
) -> dict[str, Any]:
    """Verify JWT signature against provider JWKS and return claims if valid."""
    jwks = await get_jwks_keys(issuer_url=issuer_url)
    if not jwks:
        raise JWTError("Could not fetch JWKS")

    unverified_header = jwt.get_unverified_header(id_token)
    kid = unverified_header.get("kid")
    if not kid:
        raise JWTError("No 'kid' found in JWT header")

    signing_key = None
    for jwk_key in jwks.get("keys", []):
        if jwk_key.get("kid") == kid:
            signing_key = jwk.construct(jwk_key)
            break

    if signing_key is None:
        raise JWTError(f"No matching key found for kid: {kid}")

    decode_options: dict[str, bool] = {}
    if not access_token:
        # id_token carries at_hash when issued alongside an access_token (OIDC)
        decode_options["verify_at_hash"] = False

    decode_kwargs: dict[str, Any] = {
        "token": id_token,
        "key": signing_key,
        "algorithms": ["RS256", "ES256"],
        "issuer": None,
        "options": decode_options,
    }
    if client_id:
        decode_kwargs["audience"] = client_id
    if access_token:
        decode_kwargs["access_token"] = access_token

    claims = jwt.decode(**decode_kwargs)
    logger.debug("JWT signature verified successfully")
    return claims


class AuthOidcLoginUseCase:
    REFRESH_KEY_NAME: str = "playground"

    def __init__(
        self,
        key_repository: KeyRepository,
        user_repository: UserRepository,
        sso_oidc_issuer_url: str | None = None,
        sso_oidc_client_id: str | None = None,
        login_session_duration: int = 3600,
    ):
        self.key_repository = key_repository
        self.user_repository = user_repository
        self.login_session_duration = login_session_duration
        self.sso_oidc_issuer_url = sso_oidc_issuer_url
        self.sso_oidc_client_id = sso_oidc_client_id

    async def execute(self, command: AuthOidcLoginCommand) -> AuthOidcLoginUseCaseResult:

        if not self.sso_oidc_issuer_url:
            return InvalidOidcTokenError()
        if not self.sso_oidc_client_id:
            return InvalidOidcTokenError()

        try:
            claims = await validate_oidc_id_token(id_token=command.id_token, issuer_url=self.sso_oidc_issuer_url, client_id=self.sso_oidc_client_id)
            print("####################")
            print(claims)
            print("####################")

        except JWTError as exc:
            logger.warning("SSO id_token validation failed: %s", exc)
            return InvalidOidcTokenError()

        # user = await self.user_repository.get_user_by_sub(sub=claims.get("sub"))
        # if not user:
        # create user

        user = await self.user_repository.create_user(role_id=1, email=command.email, sub=claims.get("sub"), iss=claims.get("iss"))

        expires = datetime.now(tz=UTC) + timedelta(seconds=self.login_session_duration)
        key = await self.key_repository.upsert_key(user_id=user.id, name=self.REFRESH_KEY_NAME, expire=expires)

        return AuthOidcLoginUseCaseSuccess(key=key)
