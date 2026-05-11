from jose import JWTError, jwt
from pydantic import BaseModel, Field

from api.helpers._identityaccessmanager import IdentityAccessManager
from api.infrastructure.fastapi.endpoints.exceptions import InvalidAPIKeyException


class KeyClaims(BaseModel):
    user_id: int
    key_id: int


class Key(BaseModel):
    """API Key entity"""

    value: str = Field(..., description="The raw API key value")

    def decode(self, secret_key: str) -> KeyClaims:
        if not self.value.startswith(IdentityAccessManager.TOKEN_PREFIX):
            raise InvalidAPIKeyException()

        try:
            # TODO: Refactor this. It's a duplicate with api.helpers._identityaccessmanager.IdentityAccessManager._decode_token
            jwt_token = self.value.split(IdentityAccessManager.TOKEN_PREFIX)[1]
            claims = jwt.decode(token=jwt_token, key=secret_key, algorithms=["HS256"])
            return KeyClaims(
                user_id=claims["user_id"], key_id=claims["token_id"]
            )  # TODO: ensure token_id is included in claims when creating token, test the behavior when token_id is missing but the API key has the sk- format
        except (JWTError, IndexError):
            raise InvalidAPIKeyException()
