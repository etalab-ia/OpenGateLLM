import pytest

from api.infrastructure.fastapi.schemas import reject_password_over_max_bytes


class TestRejectPasswordOverMaxBytes:
    def test_should_accept_a_72_byte_password(self):
        # Arrange
        password_of_72_bytes = "a" * 72

        # Act
        validated_password = reject_password_over_max_bytes(password_of_72_bytes)

        # Assert
        assert validated_password == password_of_72_bytes

    def test_should_reject_a_password_over_72_bytes(self):
        # Arrange
        password_of_72_characters_and_73_bytes = "a" * 71 + "é"

        # Act / Assert
        with pytest.raises(ValueError):
            reject_password_over_max_bytes(password_of_72_characters_and_73_bytes)

    def test_should_pass_none_through(self):
        # Act
        validated_password = reject_password_over_max_bytes(None)

        # Assert
        assert validated_password is None
