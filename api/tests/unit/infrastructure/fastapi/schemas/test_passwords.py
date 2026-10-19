import pytest

from api.infrastructure.fastapi.schemas import reject_password_over_max_bytes


class TestRejectPasswordOverMaxBytes:
    def test_should_accept_a_72_byte_password(self):
        password_of_72_bytes = "a" * 72

        assert reject_password_over_max_bytes(password_of_72_bytes) == password_of_72_bytes

    def test_should_reject_a_password_over_72_bytes(self):
        password_of_72_characters_and_73_bytes = "a" * 71 + "é"

        with pytest.raises(ValueError):
            reject_password_over_max_bytes(password_of_72_characters_and_73_bytes)

    def test_should_pass_none_through(self):
        assert reject_password_over_max_bytes(None) is None
