import logging
import secrets
import string
import base64
import json

from pydantic import BaseModel
import requests
import streamlit as st
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet
from ui.configuration import configuration

logger = logging.getLogger(__name__)


class User(BaseModel):
    id: int
    name: str
    api_key_id: int
    api_key: str
    proconnect_token: str | None = None

    role: dict
    user: dict


def login(user_name: str, user_password: str, proconnect_token=None) -> dict:
    # master login flow
    if user_name == configuration.playground.auth_master_username:
        response = requests.get(url=f"{configuration.playground.api_url}/v1/auth/me", headers={"Authorization": f"Bearer {user_password}"})
        if response.status_code != 404:  # only master get 404 on /auth/me
            st.error(response.json()["detail"])
            st.stop()

        response = requests.get(url=f"{configuration.playground.api_url}/v1/models", headers={"Authorization": f"Bearer {user_password}"})
        if response.status_code != 200:
            st.error(response.json()["detail"])
            st.stop()
        models = response.json()["data"]

        limits = []
        for model in models:
            limits.append({"model": model["id"], "type": "tpm", "value": None})
            limits.append({"model": model["id"], "type": "tpd", "value": None})
            limits.append({"model": model["id"], "type": "rpm", "value": None})
            limits.append({"model": model["id"], "type": "rpd", "value": None})

        role = {"object": "role", "id": 0, "name": "master", "default": False, "permissions": ["admin"], "limits": limits}
        user = User(
            id=0,
            name=configuration.playground.auth_master_username,
            api_key=user_password,
            api_key_id=0,
            proconnect_token=proconnect_token,
            user={"expires_at": None, "budget": None},
            role=role,
        )

        st.session_state["login_status"] = True
        st.session_state["user"] = user
        st.rerun()

    # basic login flow: call playground-login passing user_name and password directly
    try:
        playground_login_url = f"{configuration.playground.api_url}/v1/auth/login"
        response = requests.post(url=playground_login_url, json={"email": user_name, "password": user_password}, timeout=10)

        if response.status_code != 200:
            st.error(f"Failed to get API key: {response.json().get('detail', 'Unknown error')}")
            st.stop()

        login_data = response.json()
        api_key = login_data["api_key"]
        api_key_id = login_data["token_id"]

    except Exception as e:
        st.error(f"Authentication failed: {str(e)}")
        st.stop()

    if not api_key or not api_key_id:
        st.error("Failed to retrieve API key. Please try again.")
        st.stop()

    response = requests.get(url=f"{configuration.playground.api_url}/v1/auth/me", headers={"Authorization": f"Bearer {api_key}"})
    if response.status_code != 200:
        st.error(response.json()["detail"])
        st.stop()
    user = response.json()["user"]
    role = response.json()["role"]

    # Build a Streamlit-side user object. We don't have a local DB id anymore; use api_user id when available
    st_user_id = user.get("id") or 0
    st_user_name = user.get("name") or user.get("email") or user_name

    user = User(id=st_user_id, name=st_user_name, api_key_id=api_key_id, api_key=api_key, proconnect_token=proconnect_token, user=user, role=role)

    st.session_state["login_status"] = True
    st.session_state["user"] = user
    st.rerun()


def generate_random_password(length: int = 16) -> str:
    """Generate a secure random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def oauth_login(api_key: str, api_key_id: str, proconnect_token: str = None):
    """After OAuth2 login, backend will provide api_key and api_key_id in URL parameters and we use it to process the login"""
    response = requests.get(url=f"{configuration.playground.api_url}/v1/auth/me", headers={"Authorization": f"Bearer {api_key}"})
    if response.status_code != 200:
        st.error(response.json()["detail"])
        st.stop()
    user = response.json()["user"]
    role = response.json()["role"]

    # No local DB: use the api_key to fetch full user info and set session state directly
    st_user_id = user.get("id") or 0
    st_user_name = user.get("name") or user.get("email")

    st_user = User(id=st_user_id, name=st_user_name, api_key_id=api_key_id, api_key=api_key, proconnect_token=proconnect_token, user=user, role=role)
    st.session_state["login_status"] = True
    st.session_state["user"] = st_user
    st.query_params.clear()
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
