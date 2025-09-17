import base64
from enum import Enum
import json
import logging
import secrets
import string
from typing import List, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pydantic import BaseModel
import requests
import streamlit as st

from playground.configuration import configuration

logger = logging.getLogger(__name__)


class LimitType(str, Enum):
    TPM = "tpm"
    TPD = "tpd"
    RPM = "rpm"
    RPD = "rpd"


class Limit(BaseModel):
    model: str
    type: LimitType
    value: Optional[int] = None


class User(BaseModel):
    id: int
    email: str
    name: Optional[str] = None
    api_key_id: int
    api_key: str
    limits: List[Limit]
    permissions: List[str]
    budget: Optional[float] = None
    expires_at: Optional[int] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None
    proconnect_token: Optional[str] = None


def login(user_name: str, user_password: str) -> dict:
    response = requests.post(url=f"{configuration.playground.api_url}/v1/auth/login", json={"email": user_name, "password": user_password})
    if response.status_code != 200:
        st.error(response.json()["detail"], icon="❌")
        st.stop()

    key = response.json()

    response = requests.get(url=f"{configuration.playground.api_url}/v1/me/info", headers={"Authorization": f"Bearer {key["key"]}"})
    if response.status_code != 200:
        st.error(response.json()["detail"])
        st.stop()

    user = response.json()
    user = User(
        id=user["id"],
        email=user["email"],
        name=user["name"],
        api_key_id=key["id"],
        api_key=key["key"],
        limits=[Limit(**limit) for limit in user["limits"]],
        permissions=user["permissions"],
        budget=user["budget"],
        expires_at=user["expires_at"],
        created_at=user["created_at"],
        updated_at=user["updated_at"],
    )
    st.session_state["login_status"] = True
    st.session_state["user"] = user
    st.rerun()


def generate_random_password(length: int = 16) -> str:
    """Generate a secure random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def oauth_login(api_key: str, api_key_id: str, proconnect_token: str = None):
    """After OAuth2 login, backend will provide api_key and api_key_id in URL parameters and we use it to process the login"""
    response = requests.get(url=f"{configuration.playground.api_url}/v1/me/info", headers={"Authorization": f"Bearer {api_key}"})
    if response.status_code != 200:
        st.error(body=response.json()["detail"])
        st.stop()

    user = response.json()
    user = User(
        proconnect_token=proconnect_token,
        id=user["id"],
        email=user["email"],
        name=user["name"],
        api_key_id=api_key_id,
        api_key=api_key,
        limits=[Limit(**limit) for limit in user["limits"]],
        permissions=user["permissions"],
        budget=user["budget"],
        expires_at=user["expires_at"],
        created_at=user["created_at"],
        updated_at=user["updated_at"],
    )
    st.session_state["login_status"] = True
    st.session_state["user"] = user
    st.rerun()


def call_oauth2_logout(api_key: str, proconnect_token: str = None):
    """
    Call the logout endpoint to properly terminate OAuth2 session

    Args:
        api_token: The API token for authentication
        proconnect_token: Optional ProConnect token for ProConnect logout
    """
    logout_url = f"{configuration.playground.api_url}/v1/auth/logout"

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    # Prepare payload with optional ProConnect token
    payload = {}
    if proconnect_token:
        payload["proconnect_token"] = proconnect_token

    try:
        response = requests.post(logout_url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info("Logout successful")
        else:
            logger.warning(f"Logout endpoint returned status {response.status_code}: {response.text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to call logout endpoint: {e}")
        raise


def _get_fernet(key: str) -> Fernet:
    """Create a Fernet instance derived from the provided key (compatible with backend)."""
    try:
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=b"salt", iterations=310000)
        derived = base64.urlsafe_b64encode(kdf.derive(key.encode("utf-8")))
        return Fernet(derived)
    except Exception as exc:  # pragma: no cover - very unlikely
        logger.error("Failed to initialize Fernet for playground decryption: %s", exc)
        return None


def decrypt_oauth_token(encrypted_token: str, ttl: int = 300) -> dict | None:
    """Decrypt the token produced by the FastAPI playground redirect (returns dict or None on failure).

    This mirrors the server-side `decrypt_playground_data` logic and uses the `playground.auth_encryption_key`
    from the UI configuration. If decryption fails or the token is expired, None is returned.
    """
    try:
        key = configuration.playground.auth_encryption_key
        if not key:
            logger.warning("No playground auth_encryption_key configured, cannot decrypt token")
            return None

        fernet = _get_fernet(key=key)
        if fernet is None:
            return None

        encrypted_data = base64.urlsafe_b64decode(encrypted_token.encode())
        decrypted = fernet.decrypt(encrypted_data, ttl=ttl)
        return json.loads(decrypted.decode())
    except Exception as exc:
        logger.warning("Failed to decrypt playground encrypted_token: %s", exc)
        return None
