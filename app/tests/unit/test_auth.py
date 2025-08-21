from fastapi.testclient import TestClient

from app.main import app
from app.utils.context import global_context


class _FakeUser:
    def __init__(self, id=1):
        self.id = id


class FakeIAMSuccess:
    async def verify_user_credentials(self, session, email, password):
        return _FakeUser(id=7)

    async def refresh_token(self, session, user_id, name):
        return (99, "sk-test-token")


class FakeIAMFail:
    async def verify_user_credentials(self, session, email, password):
        return None


def test_playground_login_success():
    # Inject fake IAM that will succeed
    global_context.identity_access_manager = FakeIAMSuccess()

    client = TestClient(app)

    resp = client.post("/v1/auth/login", json={"email": "user@example.com", "password": "secret"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["api_key"] == "sk-test-token"
    assert data["token_id"] == 99


def test_playground_login_invalid_credentials():
    # Inject fake IAM that will fail verification
    global_context.identity_access_manager = FakeIAMFail()

    client = TestClient(app)

    resp = client.post("/v1/auth/login", json={"email": "user@example.com", "password": "wrong"})
    assert resp.status_code == 401
