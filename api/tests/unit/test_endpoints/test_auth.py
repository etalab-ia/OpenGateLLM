from fastapi.testclient import TestClient

from api.main import app
from api.schemas.auth import LoginResponse
from api.utils.context import global_context
from api.utils.exceptions import InvalidPasswordException


class _FakeUser:
    def __init__(self, id=1):
        self.id = id


class MockIdentityAccessManagerSuccess:
    HEADERS = {"Authorization": "Bearer sk-test-api-key"}
    LOGIN_KEY_ID = 7
    LOGIN_KEY = "sk-test-token"

    async def login(self, session, email, password):
        return self.LOGIN_KEY_ID, self.LOGIN_KEY


class MockIdentityAccessManagerFail:
    async def login(self, session, email, password):
        raise InvalidPasswordException


def test_playground_login_success():
    # Inject MockIdentityAccessManagerSuccess that will succeed
    global_context.identity_access_manager = MockIdentityAccessManagerSuccess()

    client = TestClient(app)

    response = client.post("/v1/auth/login", json={"email": "user@example.com", "password": "secret"})
    assert response.status_code == 200
    data = LoginResponse(**response.json())
    assert data.key == MockIdentityAccessManagerSuccess.LOGIN_KEY
    assert data.id == MockIdentityAccessManagerSuccess.LOGIN_KEY_ID


def test_playground_login_invalid_credentials():
    # Inject MockIdentityAccessManagerFail that will fail verification
    global_context.identity_access_manager = MockIdentityAccessManagerFail()

    client = TestClient(app)

    responses = client.post("/v1/auth/login", json={"email": "user@example.com", "password": "wrong"})
    assert responses.status_code == InvalidPasswordException().status_code
    assert responses.json()["detail"] == InvalidPasswordException().detail
