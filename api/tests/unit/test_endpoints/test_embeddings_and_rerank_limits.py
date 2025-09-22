from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.utils.context import global_context
from api.tests.unit.test_endpoints.mock import MockIdentityAccessManagerSuccess


class FakeLimiter:
    async def hit(self, user_id, model, type, value, cost: int | None = None):
        return True

    async def remaining(self, user_id, model, type, value):
        return value


class FakeTokenizer:
    def get_prompt_tokens(self, endpoint, body):
        return 0


class FakeClient:
    def __init__(self, max_items: int):
        self.max_items = max_items

    async def forward_request(self, method: str, json: dict, files=None, data=None, additional_data=None):
        # Return a minimal successful response shape where needed
        if json.get("input") is not None and json.get("prompt") is None:  # embeddings
            payload = {
                "object": "list",
                "data": [
                    {"object": "embedding", "index": 0, "embedding": [0.0, 0.1, 0.2]},
                ],
                "model": json.get("model", "test-embeddings"),
                "usage": {"prompt_tokens": 0, "total_tokens": 0},
            }
        else:  # rerank
            payload = {
                "id": "test-rerank",
                "object": "list",
                "data": [{"object": "rerank", "index": 0, "score": 0.5}],
                "usage": {"prompt_tokens": 0, "total_tokens": 0},
            }

        return SimpleNamespace(status_code=200, json=lambda: payload, headers={}, request=None)


class FakeModel:
    def __init__(self, max_items: int):
        self.max_items = max_items
        self.cost_prompt_tokens = 0.0
        self.cost_completion_tokens = 0.0

    async def safe_client_access(self, endpoint, handler):
        client = FakeClient(self.max_items)
        return await handler(client)

    def get_client(self, endpoint):
        return FakeClient(self.max_items)


class FakeModelRegistry:
    def __init__(self):
        self.models = ["test-embeddings", "test-rerank"]
        self.aliases = {}

    async def __call__(self, model: str):
        # Different limits per model
        max_items_by_model = {"test-embeddings": 2, "test-rerank": 3}
        return FakeModel(max_items=max_items_by_model.get(model, 2))


@pytest.fixture(autouse=True)
def setup_context():
    # Inject minimal context for AccessController and model lookup
    global_context.identity_access_manager = MockIdentityAccessManagerSuccess()
    global_context.model_registry = FakeModelRegistry()
    global_context.limiter = FakeLimiter()
    global_context.tokenizer = FakeTokenizer()
    yield


def test_embeddings_too_many_items_returns_400():
    client = TestClient(app)
    headers = MockIdentityAccessManagerSuccess.HEADERS

    # max_items for test-embeddings is 2; send 3 items
    body = {"model": "test-embeddings", "input": ["a", "b", "c"]}
    res = client.post("/v1/embeddings", json=body, headers=headers)

    assert res.status_code == 400
    assert "Too many items in embeddings request" in res.json()["detail"]
    assert "maximum allowed is 2" in res.json()["detail"]


def test_rerank_too_many_items_returns_400():
    client = TestClient(app)
    headers = MockIdentityAccessManagerSuccess.HEADERS

    # max_items for test-rerank is 3; send 4 items
    body = {"model": "test-rerank", "prompt": "q", "input": ["t1", "t2", "t3", "t4"]}
    res = client.post("/v1/rerank", json=body, headers=headers)

    assert res.status_code == 400
    assert "Too many items in rerank request" in res.json()["detail"]
    assert "maximum allowed is 3" in res.json()["detail"]


def test_embeddings_within_limit_returns_200():
    client = TestClient(app)
    headers = MockIdentityAccessManagerSuccess.HEADERS

    # max_items for test-embeddings is 2; send 2 items
    body = {"model": "test-embeddings", "input": ["a", "b"]}
    res = client.post("/v1/embeddings", json=body, headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert data["object"] == "list"
    assert "data" in data


def test_rerank_within_limit_returns_200():
    client = TestClient(app)
    headers = MockIdentityAccessManagerSuccess.HEADERS

    # max_items for test-rerank is 3; send 3 items
    body = {"model": "test-rerank", "prompt": "q", "input": ["t1", "t2", "t3"]}
    res = client.post("/v1/rerank", json=body, headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert data["object"] == "list"
    assert "data" in data
