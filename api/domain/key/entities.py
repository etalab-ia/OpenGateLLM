from jose import JWTError, jwt
from pydantic import BaseModel, Field

from api.utils.exceptions import InvalidAPIKeyException


class Key(BaseModel):
    """API Key entity"""

    TOKEN_PREFIX: str = "sk-"
    value: str = Field(..., description="The raw API key value")

    def decode(self, master_key: str) -> dict:
        if not self.raw_value.startswith(self.TOKEN_PREFIX):
            raise InvalidAPIKeyException()

        try:
            jwt_token = self.raw_value.split(self.TOKEN_PREFIX)[1]
            return jwt.decode(token=jwt_token, key=master_key, algorithms=["HS256"])
        except (JWTError, IndexError):
            raise InvalidAPIKeyException()

    @classmethod
    def from_string(cls, value: str) -> "Key":
        """Create Key from string"""
        return cls(raw_value=value)
