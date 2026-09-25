from datetime import UTC, datetime

import pytest

from api.domain.key.entities import Key
from api.domain.usage.entities import EnvironmentalImpacts
from api.domain.usage.entities import Usage as RecordedUsage
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.fastapi import RequestContext
from api.infrastructure.fastapi.decorators import set_usage_from_context
from api.infrastructure.fastapi.dependencies import request_context
from api.infrastructure.postgres.models import Usage

ROUTER_ID = 3


def _authenticated_user() -> AuthenticatedUserView:
    return AuthenticatedUserView(
        id=42,
        email="alice@example.com",
        name="Alice",
        organization_id=1,
        budget=10.0,
        permissions=[],
        limits=[],
        expires=None,
    )


def _set_request_context(**overrides) -> None:
    now = datetime.now(tz=UTC)
    context = RequestContext(
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


class TestSetUsageFromContext:
    def test_should_carry_the_user_and_cost_into_the_row(self):
        # Arrange
        _set_request_context(
            usage=RecordedUsage(
                prompt_tokens=7,
                completion_tokens=3,
                total_tokens=10,
                cost=0.02,
                impacts=EnvironmentalImpacts(kWh=1.5, kgCO2eq=2.5),
            )
        )

        # Act
        usage = set_usage_from_context(usage=Usage())

        # Assert
        assert usage.user_id == 42
        assert usage.cost == 0.02

    def test_should_leave_the_cost_none_when_nothing_was_recorded(self):
        # Arrange: the request failed before the provider was called
        _set_request_context()

        # Act
        usage = set_usage_from_context(usage=Usage())

        # Assert
        assert usage.cost is None
