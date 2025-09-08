import time
from typing import Optional

import requests
import streamlit as st

from playground.backend.common import check_password
from playground.configuration import configuration


def create_role(name: str, permissions: list, limits: list):
    response = requests.post(
        url=f"{configuration.playground.api_url}/v1/admin/roles",
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
        json={"name": name, "permissions": permissions, "limits": limits},
    )
    if response.status_code != 201:
        st.toast(response.json()["detail"], icon="❌")
        return

    st.toast("Role created", icon="✅")
    time.sleep(0.5)
    st.session_state["new_role"] = False
    st.session_state["update_role"] = False
    st.rerun()


def delete_role(role: int):
    response = requests.delete(
        url=f"{configuration.playground.api_url}/v1/admin/roles/{role}",
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )
    if response.status_code != 204:
        st.toast(response.json()["detail"], icon="❌")
        return

    st.toast("Role deleted", icon="✅")
    time.sleep(0.5)
    st.session_state["new_role"] = False
    st.session_state["update_role"] = False
    st.rerun()


def update_role(role: int, name: Optional[str] = None, permissions: Optional[list] = None, limits: Optional[list] = None):
    response = requests.patch(
        url=f"{configuration.playground.api_url}/v1/admin/roles/{role}",
        json={"name": name, "permissions": permissions, "limits": limits},
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )
    if response.status_code != 204:
        st.toast(response.json()["detail"], icon="❌")
        return

    st.toast("Role updated", icon="✅")
    time.sleep(0.5)
    st.session_state["new_role"] = False
    st.session_state["update_role"] = False
    st.rerun()


def create_user(email: str, password: str, role: int, name: Optional[str] = None, expires_at: Optional[int] = None, budget: Optional[float] = None):
    if not email:
        st.toast("User email is required", icon="❌")
        return

    if not password:
        st.toast("User password is required", icon="❌")
        return

    email = email.strip()
    name = name.strip() if name else None
    password = password.strip()

    if not check_password(password):
        return

    response = requests.post(
        url=f"{configuration.playground.api_url}/v1/admin/users",
        json={"email": email, "name": name, "role": role, "expires_at": expires_at, "budget": budget, "password": password},
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )

    if response.status_code != 201:
        st.toast(response.json()["detail"], icon="❌")
        return

    user_id = response.json()["id"]

    # create playground token
    response = requests.post(
        url=f"{configuration.playground.api_url}/v1/admin/tokens",
        json={"user": user_id, "name": "playground"},
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )

    if response.status_code != 201:
        st.toast(response.json()["detail"], icon="❌")
        return

    st.toast("User created", icon="✅")
    time.sleep(1)
    st.session_state["new_user"] = False
    st.rerun()


def delete_user(user: int):
    response = requests.delete(
        url=f"{configuration.playground.api_url}/v1/admin/users/{user}",
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )
    if response.status_code != 204:
        st.toast(response.json()["detail"], icon="❌")
        return

    st.toast("User deleted", icon="✅")
    time.sleep(0.5)
    st.rerun()


def update_user(
    user: int,
    email: Optional[str] = None,
    name: Optional[str] = None,
    current_password: Optional[str] = None,
    password: Optional[str] = None,
    role: Optional[int] = None,
    expires_at: Optional[int] = None,
    budget: Optional[float] = None,
):
    email = email.strip() if email else None
    name = name.strip() if name else None

    response = requests.patch(
        url=f"{configuration.playground.api_url}/v1/admin/users/{user}",
        json={
            "email": email,
            "name": name,
            "current_password": current_password,
            "password": password,
            "role": role,
            "expires_at": expires_at,
            "budget": budget,
        },
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )
    if response.status_code != 204:
        st.toast(response.json()["detail"], icon="❌")
        return

    # Server updated the user. No local DB update required.

    st.toast("User updated", icon="✅")
    time.sleep(0.5)
    st.rerun()


def refresh_playground_api_key(user: int):
    # create token
    response = requests.post(
        url=f"{configuration.playground.api_url}/v1/admin/tokens",
        json={"user": user, "name": "playground"},
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )

    if response.status_code != 201:
        st.toast(response.json()["detail"], icon="❌")
        return

    api_key = response.json()["token"]
    api_key_id = response.json()["id"]

    st.toast("Playground API key refreshed", icon="✅")
    time.sleep(0.5)
    st.rerun()
