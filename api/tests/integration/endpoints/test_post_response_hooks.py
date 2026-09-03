import asyncio
from unittest.mock import MagicMock

from httpx import AsyncClient
import pytest
import pytest_asyncio
import respx

from api.domain.provider.entities import ProviderType
from api.domain.role.entities import Limit, LimitType
from api.infrastructure.redis import RedisRouterRateLimiter
from api.schemas.admin.providers import ProviderCarbonFootprintZone
from api.schemas.core.configuration import LimitingStrategy
from api.schemas.models import ModelType
from api.tests.helpers import create_key
from api.tests.integration.conftest import override_global_context
from api.tests.integration.endpoints.utils import DEFAULT_PROVIDER_URL, mock_ocr_responses
from api.tests.integration.factories.mistral import MistralOcrResponseFactory
from api.tests.integration.factories.sql import LimitSQLFactory, RouterSQLFactory, UserSQLFactory
from api.utils.configuration import configuration
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.OCR}"

ROUTER_NAME = "hooks-ocr-router"
DOCUMENT = {"type": "document_url", "document_url": "https://example.com/document.pdf"}
COMPLETION_TOKENS = 10  # mock tokenizer: 10 tokens per non-empty text, an OCR request carries no textual prompt
RPM_LIMIT = 100
RPD_LIMIT = 200
TPM_LIMIT = 1000
TPD_LIMIT = 2000
LIMITS = ((LimitType.RPM, RPM_LIMIT), (LimitType.RPD, RPD_LIMIT), (LimitType.TPM, TPM_LIMIT), (LimitType.TPD, TPD_LIMIT))


@pytest.mark.asyncio(loop_scope="session")
class TestPostResponseHooks:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session, test_redis_pool, monkeypatch):
        # disables the log_usage task
        monkeypatch.setattr(configuration.settings, "monitoring_postgres_enabled", False)

        self.user = UserSQLFactory(name="Alice", email="alice@example.com")  # a regular user: admins are exempt from the router limits
        self.key = await create_key(db_session, name="user_key", user=self.user)
        self.router = RouterSQLFactory(
            user=UserSQLFactory(name="Bob", email="bob@example.com", admin_user=True),
            name=ROUTER_NAME,
            type=ModelType.IMAGE_TO_TEXT,
            free=True,  # disables the update_budget db write
            providers=1,
            providers__type=ProviderType.MISTRAL,
            providers__url=DEFAULT_PROVIDER_URL,
            providers__model_hosting_zone=ProviderCarbonFootprintZone.FRA,
        )
        for limit_type, value in LIMITS:
            LimitSQLFactory(role=self.user.role, router=self.router, type=limit_type, value=value)
        await db_session.flush()
        self.limits = [Limit(router_id=self.router.id, type=limit_type, value=value) for limit_type, value in LIMITS]

        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.side_effect = lambda text: [0] * COMPLETION_TOKENS if text else []
        with override_global_context(redis_pool=test_redis_pool, _tokenizer=mock_tokenizer):
            yield

    @respx.mock
    async def test_charges_the_router_limits_with_the_completion_tokens(self, client: AsyncClient, test_redis_pool):
        # Arrange
        mock_ocr_responses(
            respx_mock=respx,
            provider_type=ProviderType.MISTRAL,
            body=MistralOcrResponseFactory(page_count=1),
            status_code=MistralOcrResponseFactory._status_code,
        )

        # Act
        response = await client.post(
            url=URL, headers={"Authorization": f"Bearer {self.key.token}"}, json={"model": ROUTER_NAME, "document": DOCUMENT}
        )
        await asyncio.gather(*[task for task in asyncio.all_tasks() if task.get_name().startswith("hooks-")])

        # Assert
        assert response.status_code == 200, response.text

        # redis reader
        rate_limiter = RedisRouterRateLimiter(redis_pool=test_redis_pool, strategy=LimitingStrategy.FIXED_WINDOW)
        state = await rate_limiter.get_rate_limit_state(user_id=self.user.id, router_limits=self.limits, router_id=self.router.id, prompt_tokens=0)

        assert state.rpm.remaining == RPM_LIMIT - 1
        assert state.rpd.remaining == RPD_LIMIT - 1
        assert state.tpm.remaining == TPM_LIMIT - COMPLETION_TOKENS
        assert state.tpd.remaining == TPD_LIMIT - COMPLETION_TOKENS
