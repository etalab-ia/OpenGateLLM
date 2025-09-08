from typing import Literal, Optional

import requests
import streamlit as st

from playground.configuration import configuration
from playground.variables import MODEL_TYPE_AUDIO, MODEL_TYPE_EMBEDDINGS, MODEL_TYPE_IMAGE_TEXT_TO_TEXT, MODEL_TYPE_LANGUAGE, MODEL_TYPE_RERANK


@st.cache_data(show_spinner=False, ttl=configuration.playground.cache_ttl)
def get_models(
    types: list[Literal[MODEL_TYPE_LANGUAGE, MODEL_TYPE_IMAGE_TEXT_TO_TEXT, MODEL_TYPE_EMBEDDINGS, MODEL_TYPE_AUDIO, MODEL_TYPE_RERANK]] = [],
) -> list:
    response = requests.get(
        url=f"{configuration.playground.api_url}/v1/models", headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"}
    )
    if response.status_code != 200:
        try:
            st.error(response.json()["detail"])
        except requests.JSONDecodeError:
            st.error(response.text)
        return []

    models = response.json()["data"]
    if types == []:
        models = sorted([model["id"] for model in models], key=lambda x: x.lower())
    else:
        models = sorted([model["id"] for model in models if model["type"] in types], key=lambda x: x.lower())

    return models


def get_collections(offset: int = 0, limit: int = 10) -> list:
    response = requests.get(
        url=f"{configuration.playground.api_url}/v1/collections?offset={offset}&limit={limit}",
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )

    if response.status_code != 200:
        st.error(response.json()["detail"])
        return []

    data = response.json()["data"]

    return data


def get_documents(collection_id: int, offset: int = 0, limit: int = 10) -> dict:
    response = requests.get(
        url=f"{configuration.playground.api_url}/v1/documents?collection={collection_id}&offset={offset}&limit={limit}",
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )

    if response.status_code != 200:
        st.error(response.json()["detail"])
        return []

    data = response.json()["data"]

    return data


def get_tokens(offset: int = 0, limit: int = 10) -> list:
    response = requests.get(
        url=f"{configuration.playground.api_url}/v1/admin/tokens?offset={offset}&limit={limit}",
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )

    if response.status_code != 200:
        st.error(response.json()["detail"])
        return []

    return response.json()["data"]


def get_roles(
    offset: int = 0,
    limit: int = 10,
    order_by: Literal["id", "name", "created_at", "updated_at"] = "id",
    order_direction: Literal["asc", "desc"] = "asc",
):
    response = requests.get(
        url=f"{configuration.playground.api_url}/v1/admin/roles?offset={offset}&limit={limit}&order_by={order_by}&order_direction={order_direction}",
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )
    if response.status_code != 200:
        st.error(response.json()["detail"])
        return []

    data = response.json()["data"]

    return data


def get_users(
    role: int,
    offset: int = 0,
    limit: int = 100,
    order_by: Literal["id", "name", "created_at", "updated_at"] = "id",
    order_direction: Literal["asc", "desc"] = "asc",
):
    response = requests.get(
        url=f"{configuration.playground.api_url}/v1/admin/users?offset={offset}&limit={limit}&role={role}&order_by={order_by}&order_direction={order_direction}",
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
    )
    if response.status_code != 200:
        st.error(response.json()["detail"])
        return []

    data = response.json()["data"]

    return data


def format_limits(models: list, limits: Optional[list] = None) -> dict:
    limits = st.session_state["user"].limits if limits is None else limits
    formatted_limits = {}
    for model in models:
        formatted_limits[model] = {"tpm": 0, "tpd": 0, "rpm": 0, "rpd": 0}
        for limit in limits:
            if limit.model == model and limit.type == "tpm":
                formatted_limits[model]["tpm"] = limit.value
            elif limit.model == model and limit.type == "tpd":
                formatted_limits[model]["tpd"] = limit.value
            elif limit.model == model and limit.type == "rpm":
                formatted_limits[model]["rpm"] = limit.value
            elif limit.model == model and limit.type == "rpd":
                formatted_limits[model]["rpd"] = limit.value

    return formatted_limits


def check_password(password: str) -> bool:
    if len(password) < 8:
        st.toast("New password must be at least 8 characters long", icon="❌")
        return False
    if not any(char.isupper() for char in password):
        st.toast("New password must contain at least one uppercase letter", icon="❌")
        return False
    if not any(char.islower() for char in password):
        st.toast("New password must contain at least one lowercase letter", icon="❌")
        return False
    if not any(char.isdigit() for char in password):
        st.toast("New password must contain at least one digit", icon="❌")
        return False

    return True


def get_usage(
    limit: int = 50,
    page: int = 1,
    order_by: Literal["datetime", "cost", "total_tokens"] = "datetime",
    order_direction: Literal["asc", "desc"] = "desc",
    date_from: int = None,
    date_to: int = None,
) -> dict:
    """Get user usage data from the API."""
    response = requests.get(
        url=f"{configuration.playground.api_url}/v1/usage",
        headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
        params={
            "limit": limit,
            "page": page,
            "order_by": order_by,
            "order_direction": order_direction,
            **({"date_from": date_from} if date_from is not None else {}),
            **({"date_to": date_to} if date_to is not None else {}),
        },
    )

    if response.status_code != 200:
        st.error(response.json()["detail"])
        return {
            "data": [],
            "total_requests": 0,
            "total_albert_coins": 0.0,
            "total_tokens": 0,
            "total_co2": 0.0,
            "page": 1,
            "limit": limit,
            "total_pages": 0,
            "has_more": False,
        }

    return response.json()
