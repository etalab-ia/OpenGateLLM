from datetime import UTC, datetime, timedelta
from unittest.mock import create_autospec

import pytest

from api.domain import EntitiesPage
from api.domain.usage import UsageRepository
from api.domain.usage.entities import EnvironmentalImpacts, UsageBucket
from api.use_cases.usage import GetUsagesCommand, GetUsagesUseCase, GetUsagesUseCaseSuccess


@pytest.fixture
def mock_usage_repository():
    return create_autospec(UsageRepository, instance=True, spec_set=True)


@pytest.fixture
def use_case(mock_usage_repository):
    return GetUsagesUseCase(usage_repository=mock_usage_repository)


def _bucket(*, start: datetime) -> UsageBucket:
    return UsageBucket(
        start_time=start,
        end_time=start + timedelta(days=1),
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30,
        cost=0.1,
        impacts=EnvironmentalImpacts(kWh=0.01, kgCO2eq=0.02),
    )


class TestGetUsagesUseCase:
    @pytest.mark.asyncio
    async def test_should_return_usage_buckets_page(self, use_case, mock_usage_repository):
        # Arrange
        bucket = _bucket(start=datetime(2026, 8, 1, tzinfo=UTC))
        mock_usage_repository.get_usage_buckets_page.return_value = EntitiesPage(total=1, data=[bucket])
        command = GetUsagesCommand(
            user_id=42,
            offset=0,
            limit=10,
            start_time=1_700_000_000,
            end_time=1_800_000_000,
            endpoint="/v1/chat/completions",
            models=["model-a", "model-b"],
            key_id=7,
        )

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, GetUsagesUseCaseSuccess)
        assert result.usage_page.total == 1
        assert result.usage_page.data == [bucket]
        mock_usage_repository.get_usage_buckets_page.assert_awaited_once_with(
            user_id=42,
            start_time=datetime.fromtimestamp(1_700_000_000, tz=UTC),
            end_time=datetime.fromtimestamp(1_800_000_000, tz=UTC),
            offset=0,
            limit=10,
            endpoint="/v1/chat/completions",
            models=["model-a", "model-b"],
            key_id=7,
        )
