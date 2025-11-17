from unittest.mock import AsyncMock, MagicMock

import pytest

from api.schemas.core.metrics import Metric
from api.utils.qos import apply_async_qos_policy, apply_sync_qos_policy
from api.utils.variables import PREFIX__REDIS_METRIC_GAUGE


class TestApplySyncQosPolicy:
    def test_apply_sync_qos_policy_return_true_when_inflight_requests_within_limit(self):
        # Given
        provider_id = 1
        qos_metric = Metric.INFLIGHT
        qos_limit = 10.0
        redis_client = MagicMock()
        redis_client.get.return_value = b"5"
        # When
        result = apply_sync_qos_policy(provider_id, qos_metric, qos_limit, redis_client)
        # Then
        assert result is True
        redis_client.get.assert_called_once_with(f"{PREFIX__REDIS_METRIC_GAUGE}:{Metric.INFLIGHT.value}:{provider_id}")

    def test_apply_sync_qos_policy_return_false_when_inflight_requests_exceeds_limit(self):
        # Given
        provider_id = 1
        qos_metric = Metric.INFLIGHT
        qos_limit = 10.0
        redis_client = MagicMock()
        redis_client.get.return_value = b"15"
        # When
        result = apply_sync_qos_policy(provider_id, qos_metric, qos_limit, redis_client)
        # Then
        assert result is False
        redis_client.get.assert_called_once_with(f"{PREFIX__REDIS_METRIC_GAUGE}:{Metric.INFLIGHT.value}:{provider_id}")

    def test_apply_sync_qos_policy_return_false_when_inflight_requests_equals_limit(self):
        # Given
        provider_id = 1
        qos_metric = Metric.INFLIGHT
        qos_limit = 10.0
        redis_client = MagicMock()
        redis_client.get.return_value = b"10"
        # When
        result = apply_sync_qos_policy(provider_id, qos_metric, qos_limit, redis_client)
        # Then
        assert result is True
        redis_client.get.assert_called_once_with(f"{PREFIX__REDIS_METRIC_GAUGE}:{Metric.INFLIGHT.value}:{provider_id}")

    def test_apply_sync_qos_policy_return_true_when_inflight_requests_not_in_redis(self):
        # Given
        provider_id = 1
        qos_metric = Metric.INFLIGHT
        qos_limit = 10.0
        redis_client = MagicMock()
        redis_client.get.return_value = None
        # When
        result = apply_sync_qos_policy(provider_id, qos_metric, qos_limit, redis_client)
        # Then
        assert result is True
        redis_client.get.assert_called_once_with(f"{PREFIX__REDIS_METRIC_GAUGE}:{Metric.INFLIGHT.value}:{provider_id}")

    def test_apply_sync_qos_policy_return_true_when_qos_limit_is_none(self):
        # Given
        provider_id = 1
        qos_metric = Metric.INFLIGHT
        qos_limit = None
        redis_client = MagicMock()
        redis_client.get.return_value = b"15"
        # When
        result = apply_sync_qos_policy(provider_id, qos_metric, qos_limit, redis_client)
        # Then
        assert result is True
        redis_client.get.assert_not_called()

    def test_apply_sync_qos_policy_return_true_when_qos_metric_is_not_inflight(self):
        # Given
        provider_id = 1
        qos_metric = Metric.LATENCY
        qos_limit = 10.0
        redis_client = MagicMock()
        # When
        result = apply_sync_qos_policy(provider_id, qos_metric, qos_limit, redis_client)
        # Then
        assert result is True
        redis_client.get.assert_not_called()

    def test_apply_sync_qos_policy_return_true_when_both_inflight_requests_and_qos_limit_are_none(self):
        # Given
        provider_id = 1
        qos_metric = Metric.INFLIGHT
        qos_limit = None
        redis_client = MagicMock()
        redis_client.get.return_value = None
        # When
        result = apply_sync_qos_policy(provider_id, qos_metric, qos_limit, redis_client)
        # Then
        assert result is True
        redis_client.get.assert_not_called()


class TestApplyAsyncQosPolicy:
    @pytest.mark.asyncio
    async def test_apply_async_qos_policy_return_true_when_inflight_requests_within_limit(self):
        # Given
        provider_id = 1
        qos_metric = Metric.INFLIGHT
        qos_limit = 10.0
        redis_client = AsyncMock()
        redis_client.get.return_value = b"5"
        # When
        result = await apply_async_qos_policy(provider_id, qos_metric, qos_limit, redis_client)
        # Then
        assert result is True
        redis_client.get.assert_awaited_once_with(f"{PREFIX__REDIS_METRIC_GAUGE}:{Metric.INFLIGHT.value}:{provider_id}")

    @pytest.mark.asyncio
    async def test_apply_async_qos_policy_return_false_when_inflight_requests_exceeds_limit(self):
        # Given
        provider_id = 1
        qos_metric = Metric.INFLIGHT
        qos_limit = 10.0
        redis_client = AsyncMock()
        redis_client.get.return_value = b"15"
        # When
        result = await apply_async_qos_policy(provider_id, qos_metric, qos_limit, redis_client)
        # Then
        assert result is False
        redis_client.get.assert_awaited_once_with(f"{PREFIX__REDIS_METRIC_GAUGE}:{Metric.INFLIGHT.value}:{provider_id}")

    @pytest.mark.asyncio
    async def test_apply_async_qos_policy_return_true_when_inflight_requests_equals_limit(self):
        # Given
        provider_id = 1
        qos_metric = Metric.INFLIGHT
        qos_limit = 10.0
        redis_client = AsyncMock()
        redis_client.get.return_value = b"10"
        # When
        result = await apply_async_qos_policy(provider_id, qos_metric, qos_limit, redis_client)
        # Then
        assert result is True
        redis_client.get.assert_awaited_once_with(f"{PREFIX__REDIS_METRIC_GAUGE}:{Metric.INFLIGHT.value}:{provider_id}")

    @pytest.mark.asyncio
    async def test_apply_async_qos_policy_return_true_when_inflight_requests_not_in_redis(self):
        # Given
        provider_id = 1
        qos_metric = Metric.INFLIGHT
        qos_limit = 10.0
        redis_client = AsyncMock()
        redis_client.get.return_value = None
        # When
        result = await apply_async_qos_policy(provider_id, qos_metric, qos_limit, redis_client)
        # Then
        assert result is True
        redis_client.get.assert_awaited_once_with(f"{PREFIX__REDIS_METRIC_GAUGE}:{Metric.INFLIGHT.value}:{provider_id}")

    @pytest.mark.asyncio
    async def test_apply_async_qos_policy_return_true_when_qos_limit_is_none(self):
        # Given
        provider_id = 1
        qos_metric = Metric.INFLIGHT
        qos_limit = None
        redis_client = AsyncMock()
        redis_client.get.return_value = b"15"
        # When
        result = await apply_async_qos_policy(provider_id, qos_metric, qos_limit, redis_client)
        # Then
        assert result is True
        redis_client.get.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_apply_async_qos_policy_return_true_when_qos_metric_is_not_inflight(self):
        # Given
        provider_id = 1
        qos_metric = Metric.LATENCY
        qos_limit = 10.0
        redis_client = AsyncMock()
        # When
        result = await apply_async_qos_policy(provider_id, qos_metric, qos_limit, redis_client)
        # Then
        assert result is True
        redis_client.get.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_apply_async_qos_policy_return_true_when_both_inflight_requests_and_qos_limit_are_none(self):
        # Given
        provider_id = 1
        qos_metric = Metric.INFLIGHT
        qos_limit = None
        redis_client = AsyncMock()
        redis_client.get.return_value = None
        # When
        result = await apply_async_qos_policy(provider_id, qos_metric, qos_limit, redis_client)
        # Then
        assert result is True
        redis_client.get.assert_not_awaited()
