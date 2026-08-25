from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from api.domain import EntitiesPage
from api.domain.usage.entities import EnvironmentalImpacts, UsageRecord
from api.use_cases.usage import GetUsagesCommand, GetUsagesUseCase, GetUsagesUseCaseSuccess


@pytest.fixture
def usage_repository():
    return AsyncMock()


@pytest.fixture
def use_case(usage_repository):
    return GetUsagesUseCase(usage_repository=usage_repository)


class TestGetUsagesUseCase:
    @pytest.mark.asyncio
    async def test_should_return_usages_page(self, use_case, usage_repository):
        # Arrange
        usage = UsageRecord(
            model="model-a",
            key="key-a",
            endpoint="/v1/chat/completions",
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            cost=0.1,
            latency=100,
            ttft=50,
            impacts=EnvironmentalImpacts(kWh=0.01, kgCO2eq=0.02),
            created=datetime(2026, 8, 1, tzinfo=UTC),
        )
        usage_repository.get_usages_page.return_value = EntitiesPage(total=1, data=[usage])
        command = GetUsagesCommand(
            user_id=42,
            offset=0,
            limit=10,
            start_time=1_700_000_000,
            end_time=1_800_000_000,
            endpoint="/v1/chat/completions",
        )

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, GetUsagesUseCaseSuccess)
        assert result.usage_page.total == 1
        assert result.usage_page.data == [usage]
        usage_repository.get_usages_page.assert_awaited_once_with(
            user_id=42,
            start_time=datetime.fromtimestamp(1_700_000_000, tz=UTC),
            end_time=datetime.fromtimestamp(1_800_000_000, tz=UTC),
            offset=0,
            limit=10,
            endpoint="/v1/chat/completions",
        )

    @pytest.mark.asyncio
    async def test_should_default_time_window_to_last_30_days(self, use_case, usage_repository):
        # Arrange
        frozen_now = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)
        usage_repository.get_usages_page.return_value = EntitiesPage(total=0, data=[])
        command = GetUsagesCommand(user_id=42, offset=0, limit=10, start_time=None, end_time=None, endpoint=None)

        # Act
        with patch("api.use_cases.usage._getusagesusecase.dt.datetime") as mock_datetime:
            mock_datetime.now.return_value = frozen_now
            mock_datetime.fromtimestamp = datetime.fromtimestamp
            result = await use_case.execute(command)

        # Assert
        assert isinstance(result, GetUsagesUseCaseSuccess)
        usage_repository.get_usages_page.assert_awaited_once_with(
            user_id=42,
            start_time=frozen_now - timedelta(days=30),
            end_time=frozen_now,
            offset=0,
            limit=10,
            endpoint=None,
        )
