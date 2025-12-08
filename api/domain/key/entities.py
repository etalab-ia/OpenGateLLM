from jose import JWTError, jwt
from pydantic import BaseModel, Field

from api.utils.exceptions import InvalidAPIKeyException

MASTER_USER_ID = 0
MASTER_KEY_ID = 0


class KeyClaims(BaseModel):
    user_id: int
    key_id: int


class Key(BaseModel):
    """API Key entity"""

    TOKEN_PREFIX: str = "sk-"
    value: str = Field(..., description="The raw API key value")

    def decode(self, master_key: str) -> KeyClaims:
        if self.value == master_key:
            return KeyClaims(user_id=MASTER_USER_ID, key_id=MASTER_KEY_ID)

        if not self.value.startswith(self.TOKEN_PREFIX):
            raise InvalidAPIKeyException()

        try:
            jwt_token = self.value.split(self.TOKEN_PREFIX)[1]
            claims = jwt.decode(token=jwt_token, key=master_key, algorithms=["HS256"])
            return KeyClaims(user_id=claims["user_id"], key_id=claims["token_id"])
        except (JWTError, IndexError):
            raise InvalidAPIKeyException()
