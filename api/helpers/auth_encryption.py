import base64
import json
import logging
import time

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from fastapi import HTTPException

from api.utils.configuration import configuration

logger = logging.getLogger(__name__)


def get_fernet(key: str) -> Fernet:
    """
    Initialize Fernet encryption using a master key from configuration.
    """
    try:
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=b"salt", iterations=310000)
        derived = base64.urlsafe_b64encode(kdf.derive(key.encode("utf-8")))
        return Fernet(derived)
    except Exception as e:
        logger.error(f"Failed to initialize Fernet encryption: {e}")
        raise HTTPException(status_code=500, detail="Encryption initialization failed")


def encrypt_redirect_data(app_token: str, token_id: str, proconnect_token: str) -> str:
    """
    Encrypt data for playground redirection.

    Args:
        app_token: The application token (API key)
        token_id: The ID of the token in the database
        proconnect_token: The ProConnect token for OAuth2 session to be used for logout
    """
    try:
        fernet = get_fernet(key=configuration.settings.auth_master_key)
        data = {
            "app_token": app_token,
            "token_id": token_id,
            "proconnect_token": proconnect_token,
            "timestamp": int(time.time()),
        }

        json_data = json.dumps(data)
        encrypted_data = fernet.encrypt(json_data.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()
    except Exception as e:
        logger.error(f"Failed to encrypt redirect data: {e}")
        raise HTTPException(status_code=500, detail="Encryption failed")


def decrypt_playground_data(encrypted_token: str, ttl: int = 300) -> dict:
    """
    Decrypt redirect data from encrypted token with TTL validation.

    Args:
        encrypted_token: The encrypted token to decrypt
        ttl: Time to live in seconds (default 5 minutes)

        Returns:
        Dictionary containing decrypted data
    """
    try:
        fernet = get_fernet(key=configuration.settings.auth_master_key)
        encrypted_data = base64.urlsafe_b64decode(encrypted_token.encode())
        decrypted_data = fernet.decrypt(encrypted_data, ttl=ttl)
        data = json.loads(decrypted_data.decode())
        return data
    except Exception as e:
        logger.error(f"Failed to decrypt playground data: {e}")
        raise HTTPException(status_code=400, detail="Invalid or expired token")
