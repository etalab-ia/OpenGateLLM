from unittest.mock import create_autospec

import pytest

from api.domain.model import ModelQuery
from api.domain.role.entities import Limit, LimitType
from api.domain.router import RouterRateLimiter
from api.domain.router.entities import RouterRateLimitState, RpdRateLimitState, RpmRateLimitState, TpdRateLimitState, TpmRateLimitState
from api.domain.router.views import RouterLimitsView, RouterLimitView
from api.tests.unit.use_case.factories import AuthenticatedUserFactory, ModelViewFactory
from api.use_cases.limits import GetLimitsCommand, GetLimitsUseCase, GetLimitsUseCaseSuccess


@pytest.fixture
def mock_model_query():
    return create_autospec(ModelQuery, instance=True, spec_set=True)


@pytest.fixture
def mock_router_rate_limiter():
    return create_autospec(RouterRateLimiter, instance=True, spec_set=True)


@pytest.fixture
def use_case(mock_model_query, mock_router_rate_limiter):
    return GetLimitsUseCase(model_query=mock_model_query, router_rate_limiter=mock_router_rate_limiter)


class TestGetLimitsUseCase:
    @pytest.mark.asyncio
    async def test_should_return_the_limits_of_an_allowed_router_from_the_rate_limiter(self, mock_model_query, mock_router_rate_limiter, use_case):
        # Arrange
        user = AuthenticatedUserFactory(
            without_permission=True,
            limits=[Limit(router_id=1, type=LimitType.RPM, value=20), Limit(router_id=1, type=LimitType.TPM, value=None)],
        )
        mock_model_query.get_models.return_value = [ModelViewFactory(router_id=1, id="model-1")]
        mock_router_rate_limiter.get_rate_limit_state.return_value = RouterRateLimitState(
            tpm=TpmRateLimitState(value=None),
            tpd=TpdRateLimitState(value=10000, remaining=5000),
            rpm=RpmRateLimitState(value=20, remaining=1),
            rpd=RpdRateLimitState(value=10000, remaining=40),
        )

        # Act
        result = await use_case.execute(command=GetLimitsCommand(authenticated_user=user))

        # Assert
        assert isinstance(result, GetLimitsUseCaseSuccess)
        assert result.limits == [
            RouterLimitsView(
                router_id=1,
                model="model-1",
                limits=[
                    RouterLimitView(type=LimitType.TPM, value=None, remaining=0),
                    RouterLimitView(type=LimitType.TPD, value=10000, remaining=5000),
                    RouterLimitView(type=LimitType.RPM, value=20, remaining=1),
                    RouterLimitView(type=LimitType.RPD, value=10000, remaining=40),
                ],
            )
        ]
        mock_router_rate_limiter.get_rate_limit_state.assert_awaited_once_with(user_id=user.id, router_limits=user.limits, router_id=1)

    @pytest.mark.asyncio
    async def test_should_return_every_limit_unlimited_without_reading_the_rate_limiter_when_the_user_is_admin(
        self, mock_model_query, mock_router_rate_limiter, use_case
    ):
        # Arrange
        user = AuthenticatedUserFactory(admin=True, limits=[])
        mock_model_query.get_models.return_value = [ModelViewFactory(router_id=1, id="model-1")]

        # Act
        result = await use_case.execute(command=GetLimitsCommand(authenticated_user=user))

        # Assert
        assert isinstance(result, GetLimitsUseCaseSuccess)
        assert [limit.value for limit in result.limits[0].limits] == [None, None, None, None]
        mock_router_rate_limiter.get_rate_limit_state.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_leave_out_a_router_the_user_cannot_access(self, mock_model_query, mock_router_rate_limiter, use_case):
        # Arrange
        user = AuthenticatedUserFactory(without_permission=True, limits=[Limit(router_id=1, type=LimitType.RPM, value=20)])
        mock_model_query.get_models.return_value = [ModelViewFactory(router_id=1, id="model-1"), ModelViewFactory(router_id=2, id="model-2")]
        mock_router_rate_limiter.get_rate_limit_state.return_value = RouterRateLimitState()

        # Act
        result = await use_case.execute(command=GetLimitsCommand(authenticated_user=user))

        # Assert
        assert isinstance(result, GetLimitsUseCaseSuccess)
        assert [router_limits.model for router_limits in result.limits] == ["model-1"]
        mock_router_rate_limiter.get_rate_limit_state.assert_awaited_once_with(user_id=user.id, router_limits=user.limits, router_id=1)
