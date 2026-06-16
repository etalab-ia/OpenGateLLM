from re import sub
from typing import Any
from urllib.parse import urljoin

import factory
from fastapi import FastAPI
from fastapi.routing import APIRoute
import httpx

from api.domain.provider.entities import ProviderType
from api.infrastructure.fastapi import AccessController

DEFAULT_PROVIDER_URL = "http://my-test-provider/"
NOT_ADMIN_USER_DETAIL = "User has no admin rights."

MODELS_ENDPOINT_BY_PROVIDER = {
    ProviderType.ALBERT: "/v1/models",
    ProviderType.MISTRAL: "/v1/models",
    ProviderType.OPENAI: "/v1/models",
    ProviderType.TEI: "/info",
    ProviderType.VLLM: "/v1/models",
}
METRICS_ENDPOINT_BY_PROVIDER = {
    ProviderType.VLLM: "/metrics",
    ProviderType.MISTRAL: "/metrics",
}
EMBEDDINGS_ENDPOINT_BY_PROVIDER = {
    ProviderType.ALBERT: "/v1/embeddings",
    ProviderType.MISTRAL: "/v1/embeddings",
    ProviderType.OPENAI: "/v1/embeddings",
    ProviderType.TEI: "/v1/embeddings",
    ProviderType.VLLM: "/v1/embeddings",
}
RERANK_ENDPOINT_BY_PROVIDER = {
    ProviderType.TEI: "/rerank",
    ProviderType.VLLM: "/v2/rerank",
}


def mock_models_responses(respx_mock, provider_type: ProviderType, body: factory.DictFactory, status_code: int) -> None:
    url = urljoin(DEFAULT_PROVIDER_URL, MODELS_ENDPOINT_BY_PROVIDER[provider_type])
    respx_mock.get(url=url).mock(return_value=httpx.Response(status_code=status_code, json=body))


def mock_embeddings_responses(respx_mock, provider_type: ProviderType, body: factory.DictFactory, status_code: int) -> None:
    url = urljoin(DEFAULT_PROVIDER_URL, url=EMBEDDINGS_ENDPOINT_BY_PROVIDER[provider_type])
    respx_mock.post(url=url).mock(return_value=httpx.Response(status_code=status_code, json=body))


def mock_rerank_responses(respx_mock, provider_type: ProviderType, body: list | factory.Factory, status_code: int) -> None:
    url = urljoin(DEFAULT_PROVIDER_URL, RERANK_ENDPOINT_BY_PROVIDER[provider_type])
    respx_mock.post(url=url).mock(return_value=httpx.Response(status_code=status_code, json=body))


def mock_metrics_responses(respx_mock, provider_type: ProviderType, text: str, status_code: int) -> None:
    url = urljoin(DEFAULT_PROVIDER_URL, METRICS_ENDPOINT_BY_PROVIDER[provider_type])
    respx_mock.get(url=url).mock(return_value=httpx.Response(status_code=status_code, text=text, headers={"Content-Type": "text/plain"}))


def _fill_path_params(path: str) -> str:
    return sub(r"\{[^}]+\}", "1", path)


def _is_access_controller(dependency: Any) -> AccessController | None:
    candidate = getattr(dependency, "dependency", dependency)
    return candidate if isinstance(candidate, AccessController) else None


def collect_routes_by_access_controller(app: FastAPI, *, only_admin: bool) -> list[tuple[str, str]]:
    routes: list[tuple[str, str]] = []

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        access_controller = next(
            (controller for dependency in route.dependencies if (controller := _is_access_controller(dependency)) is not None),
            None,
        )
        if access_controller is None or access_controller.only_admin is not only_admin:
            continue

        for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
            routes.append((method, _fill_path_params(route.path)))

    return routes


def collect_admin_only_routes(app: FastAPI) -> list[tuple[str, str]]:
    return collect_routes_by_access_controller(app, only_admin=True)


def collect_authenticated_non_admin_routes(app: FastAPI) -> list[tuple[str, str]]:
    return collect_routes_by_access_controller(app, only_admin=False)
