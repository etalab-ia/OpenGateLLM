from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from api.domain.key.entities import Key
from api.domain.role.entities import Limit, LimitType, PermissionType
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.fastapi import RequestContext
from api.infrastructure.fastapi.decorators import charge_router_limits, set_usage_from_context
from api.infrastructure.fastapi.dependencies import request_context
from api.sql.models import Usage

ROUTER_ID = 3
OTHER_ROUTER_ID = 4


def _authenticated_user(permissions: list[PermissionType] | None = None, limits: list[Limit] | None = None) -> AuthenticatedUserView:
    return AuthenticatedUserView(
        id=42,
        email="alice@example.com",
        name="Alice",
        organization_id=None,
        budget=10.0,
        permissions=permissions if permissions is not None else [],
        limits=limits if limits is not None else [],
        expires=None,
    )


def _set_request_context(**overrides) -> None:
    now = datetime.now(tz=UTC)
    context = RequestContext(
        method="POST",
        endpoint="/v1/ocr",
        key=Key(id=7, name="my-key", user_id=42, value="sk-...", expires=None, created=now),
        user=_authenticated_user(),
        router_id=ROUTER_ID,
        provider_id=8,
        router_name="ocr-router",
        provider_model_name="ocr-provider",
        **overrides,
    )
    request_context.set(context)


@pytest.fixture(autouse=True)
def reset_request_context():
    token = request_context.set(RequestContext())
    yield
    request_context.reset(token)


@pytest.fixture
def mock_router_rate_limiter():
    return AsyncMock()


class TestSetUsageFromContext:
    def test_should_sum_prompt_and_completion_tokens_into_total_tokens(self):
        # Arrange
        _set_request_context(prompt_tokens=7, completion_tokens=3)

        # Act
        usage = set_usage_from_context(usage=Usage())

        # Assert
        assert usage.prompt_tokens == 7
        assert usage.completion_tokens == 3
        assert usage.total_tokens == 10

    def test_should_leave_total_tokens_none_when_no_token_was_recorded(self):
        # Arrange: the request failed before the provider was called
        _set_request_context(prompt_tokens=None, completion_tokens=None)

        # Act
        usage = set_usage_from_context(usage=Usage())

        # Assert
        assert usage.total_tokens is None


@pytest.mark.asyncio
class TestChargeRouterLimits:
    async def test_should_charge_the_router_limits_with_prompt_and_completion_tokens(self, mock_router_rate_limiter):
        # Arrange
        router_limit = Limit(router_id=ROUTER_ID, type=LimitType.TPM, value=100)
        other_router_limit = Limit(router_id=OTHER_ROUTER_ID, type=LimitType.TPM, value=100)
        user = _authenticated_user(limits=[router_limit, other_router_limit])
        usage = Usage(router_id=ROUTER_ID, prompt_tokens=7, completion_tokens=3)

        # Act
        await charge_router_limits(user=user, usage=usage, router_rate_limiter_provider=lambda: mock_router_rate_limiter)

        # Assert
        mock_router_rate_limiter.update_rate_limit_state.assert_awaited_once_with(
            user_id=user.id,
            router_limits=[router_limit],
            router_id=ROUTER_ID,
            prompt_tokens=7,
            completion_tokens=3,
        )

    async def test_should_charge_zero_tokens_when_none_was_recorded(self, mock_router_rate_limiter):
        # Arrange: the request failed after the router was resolved
        user = _authenticated_user(limits=[Limit(router_id=ROUTER_ID, type=LimitType.RPM, value=10)])
        usage = Usage(router_id=ROUTER_ID)

        # Act
        await charge_router_limits(user=user, usage=usage, router_rate_limiter_provider=lambda: mock_router_rate_limiter)

        # Assert
        assert mock_router_rate_limiter.update_rate_limit_state.await_args.kwargs["prompt_tokens"] == 0
        assert mock_router_rate_limiter.update_rate_limit_state.await_args.kwargs["completion_tokens"] == 0

    async def test_should_skip_admin_users(self, mock_router_rate_limiter):
        # Arrange
        user = _authenticated_user(permissions=[PermissionType.ADMIN])
        usage = Usage(router_id=ROUTER_ID, prompt_tokens=7, completion_tokens=3)

        # Act
        await charge_router_limits(user=user, usage=usage, router_rate_limiter_provider=lambda: mock_router_rate_limiter)

        # Assert
        mock_router_rate_limiter.update_rate_limit_state.assert_not_awaited()

    async def test_should_skip_when_no_router_was_resolved(self, mock_router_rate_limiter):
        # Arrange: the request failed before the router was resolved
        usage = Usage(prompt_tokens=7, completion_tokens=3)

        # Act
        await charge_router_limits(user=_authenticated_user(), usage=usage, router_rate_limiter_provider=lambda: mock_router_rate_limiter)

        # Assert
        mock_router_rate_limiter.update_rate_limit_state.assert_not_awaited()

    async def test_should_swallow_rate_limiter_failures(self, mock_router_rate_limiter):
        # Arrange: the hook runs after the response, a failure must not bubble up
        mock_router_rate_limiter.update_rate_limit_state.side_effect = RuntimeError("redis is down")
        usage = Usage(router_id=ROUTER_ID, prompt_tokens=7, completion_tokens=3)

        # Act / Assert
        await charge_router_limits(user=_authenticated_user(), usage=usage, router_rate_limiter_provider=lambda: mock_router_rate_limiter)
