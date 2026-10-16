import pytest

from api.infrastructure.fastapi.schemas import MAX_PASSWORD_BYTES, reject_password_over_max_bytes


class TestRejectPasswordOverMaxBytes:
    def test_should_accept_ascii_password_at_the_byte_limit(self):
        password = "a" * MAX_PASSWORD_BYTES

        assert reject_password_over_max_bytes(password) == password

    def test_should_accept_password_below_the_byte_limit(self):
        assert reject_password_over_max_bytes("s3cr3t") == "s3cr3t"

    def test_should_reject_multibyte_password_over_the_byte_limit(self):
        # 72 accented characters encode to 144 bytes, past bcrypt's 72-byte budget
        with pytest.raises(ValueError):
            reject_password_over_max_bytes("é" * MAX_PASSWORD_BYTES)

    def test_should_pass_none_through(self):
        assert reject_password_over_max_bytes(None) is None
