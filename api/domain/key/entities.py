from jose import JWTError, jwt
from pydantic import BaseModel, Field

from api.helpers._identityaccessmanager import IdentityAccessManager
from api.utils.exceptions import InvalidAPIKeyException

MASTER_ID: int = 0


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
            # TODO: Duplicate with api.helpers._identityaccessmanager.IdentityAccessManager._decode_token
            jwt_token = self.value.split(IdentityAccessManager.TOKEN_PREFIX)[1]
            claims = jwt.decode(token=jwt_token, key=secret_key, algorithms=["HS256"])
            return KeyClaims(
                user_id=claims["user_id"], key_id=claims["token_id"]
            )  # TODO: ensure token_id is included in claims when creating token, test the behavior when token_id is missing but the API key has the sk- format
        except (JWTError, IndexError):
            raise InvalidAPIKeyException()
