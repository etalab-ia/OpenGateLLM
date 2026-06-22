from jose import JWTError, jwk, jwt

from api.domain.auth import AuthSsoTokenValidator
from api.domain.auth.errors import InvalidOidcTokenError


class JwtAuthSsoTokenValidator(AuthSsoTokenValidator):
    async def validate_token(self, token: str, client_id: str, jwks: dict) -> dict[str] | InvalidOidcTokenError:
        unverified_header = jwt.get_unverified_header(token=token)
        kid = unverified_header.get("kid")
        if not kid:
            return InvalidOidcTokenError(message="No 'kid' found in JWT header")

        signing_key = None
        for jwk_key in jwks.get("keys", []):
            if jwk_key.get("kid") == kid:
                signing_key = jwk.construct(jwk_key)
                break

        if signing_key is None:
            return InvalidOidcTokenError(message=f"No matching key found for kid: {kid}", stale_jwks=True)

        decode_kwargs: dict[str] = {
            "token": token,
            "key": signing_key,
            "algorithms": ["RS256", "ES256"],
            "issuer": None,
            "audience": client_id,
            "options": {"verify_at_hash": False},
        }

        try:
            claims = jwt.decode(**decode_kwargs)
        except JWTError as e:
            return InvalidOidcTokenError(message=f"JWT validation failed: {e}")

        return claims
