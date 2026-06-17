from jose import jwt
from pydantic import FutureDatetime

from api.domain.key import KeyEncoder


class JwtKeyEncoder(KeyEncoder):
    def __init__(self, secret_key: str):
        self.secret_key = secret_key

    def encode_token(self, user_id: int, key_id: int, expires: FutureDatetime | None = None) -> str:
        expires = int(expires.timestamp()) if expires is not None else None
        return KeyEncoder.KEY_PREFIX + jwt.encode(
            claims={"user_id": user_id, "token_id": key_id, "expires": expires},
            key=self.secret_key,
            algorithm=self.ENCODING_ALGORITHM,
        )

    def decode(self, key_value: str) -> dict:
        value = key_value.split(KeyEncoder.KEY_PREFIX)[1]
        return jwt.decode(token=value, key=self.secret_key, algorithms=[self.ENCODING_ALGORITHM])
