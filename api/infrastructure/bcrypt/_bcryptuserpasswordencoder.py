import bcrypt

from api.domain.user import UserPasswordEncoder


class BcryptUserPasswordEncoder(UserPasswordEncoder):
    def encode_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def validate_password(self, password: str, encoded_password: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8"), encoded_password.encode("utf-8"))
