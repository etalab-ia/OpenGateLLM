import pytest

from api.infrastructure.bcrypt import BcryptUserPasswordEncoder


@pytest.fixture
def password_encoder() -> BcryptUserPasswordEncoder:
    return BcryptUserPasswordEncoder()


class TestBcryptUserPasswordEncoder:
    def test_encode_password_returns_bcrypt_hash(self, password_encoder: BcryptUserPasswordEncoder):
        # Act
        encoded = password_encoder.encode_password("plaintext")

        # Assert
        assert encoded != "plaintext"
        assert encoded.startswith("$2")

    def test_validate_password_returns_true_when_password_matches(self, password_encoder: BcryptUserPasswordEncoder):
        # Arrange
        encoded = password_encoder.encode_password("s3cr3t")

        # Act / Assert
        assert password_encoder.validate_password("s3cr3t", encoded) is True

    def test_validate_password_returns_false_when_password_does_not_match(self, password_encoder: BcryptUserPasswordEncoder):
        # Arrange
        encoded = password_encoder.encode_password("s3cr3t")

        # Act / Assert
        assert password_encoder.validate_password("wrong-password", encoded) is False
