from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from api.domain.usage import UsageRepository
from api.domain.usage.entities import UsageRecord
from api.use_cases.usage import CreateUsageRecordCommand, CreateUsageRecordUseCase, CreateUsageRecordUseCaseSuccess

CREATED = datetime(2026, 8, 1, 10, tzinfo=UTC)


@pytest.fixture
def mock_usage_repository():
    return create_autospec(UsageRepository, instance=True, spec_set=True)


@pytest.fixture
def use_case(mock_usage_repository):
    return CreateUsageRecordUseCase(usage_repository=mock_usage_repository)


class TestCreateUsageRecordUseCase:
    @pytest.mark.asyncio
    async def test_should_create_the_usage_record_from_the_command(self, use_case, mock_usage_repository):
        # Arrange
        command = CreateUsageRecordCommand(
            created=CREATED,
            endpoint="/v1/embeddings",
            method="POST",
            user_id=42,
            user_email="user@example.com",
            key_id=7,
            key_name="my-key",
            router_id=1,
            router_name="my-router",
            provider_id=2,
            provider_model_name="my-provider-model",
            status=200,
            prompt_tokens=10,
            completion_tokens=20,
            cost=0.3,
            kwh=0.01,
            kgco2eq=0.02,
            latency=100,
            ttft=50,
        )
        mock_usage_repository.create_usage_record.side_effect = lambda usage_record: usage_record.model_copy(update={"id": 1})

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, CreateUsageRecordUseCaseSuccess)
        assert result.usage_record.id == 1
        mock_usage_repository.create_usage_record.assert_awaited_once_with(
            usage_record=UsageRecord(
                created=CREATED,
                endpoint="/v1/embeddings",
                method="POST",
                user_id=42,
                user_email="user@example.com",
                key_id=7,
                key_name="my-key",
                router_id=1,
                router_name="my-router",
                provider_id=2,
                provider_model_name="my-provider-model",
                status=200,
                prompt_tokens=10,
                completion_tokens=20,
                cost=0.3,
                kwh=0.01,
                kgco2eq=0.02,
                latency=100,
                ttft=50,
            )
        )

    @pytest.mark.asyncio
    async def test_should_create_the_usage_record_without_optional_fields(self, use_case, mock_usage_repository):
        # Arrange
        command = CreateUsageRecordCommand(created=CREATED, endpoint="/v1/embeddings", status=429)
        mock_usage_repository.create_usage_record.side_effect = lambda usage_record: usage_record.model_copy(update={"id": 1})

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, CreateUsageRecordUseCaseSuccess)
        assert result.usage_record.total_tokens is None
        assert result.usage_record.method is None
