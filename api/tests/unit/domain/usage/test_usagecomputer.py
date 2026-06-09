from unittest.mock import Mock

import pytest

from api.domain.usage import UsageComputer
from api.domain.usage.entities import EnvironmentalImpacts, Usage


@pytest.fixture
def model_tokenizer():
    tokenizer = Mock()
    tokenizer.encode.return_value = [100, 200]
    return tokenizer


@pytest.fixture
def model_environmental_impacts_computer():
    computer = Mock()
    computer.compute.return_value = EnvironmentalImpacts(kgCO2eq=1, kWh=2)
    return computer


@pytest.fixture
def usage_computer(model_environmental_impacts_computer, model_tokenizer) -> UsageComputer:
    return UsageComputer(model_environmental_impacts_computer=model_environmental_impacts_computer, model_tokenizer=model_tokenizer)


class TestUsageComputer:
    def test_compute_tokens_joins_and_strips_texts(self, usage_computer, model_tokenizer):
        # Act
        result = usage_computer.compute_tokens(texts=["query", "document1", "document2 "])

        # Assert
        assert result == 2
        model_tokenizer.encode.assert_called_once_with("query document1 document2")

    def test_compute_cost_correctly(self):
        # Act
        result = UsageComputer._compute_cost(prompt_tokens=100, completion_tokens=100, cost_prompt_tokens=1.0, cost_completion_tokens=2.0)

        # Assert
        assert result == 0.0003

    def test_compute_usage(self, usage_computer, model_environmental_impacts_computer):
        # Act
        result = usage_computer.compute_usage(
            prompt_tokens=100,
            completion_tokens=100,
            cost_prompt_tokens=1.0,
            cost_completion_tokens=2.0,
            latency=20,
            model_active_params=5,
            model_total_params=10,
            model_hosting_zone="WOR",
        )

        # Assert
        model_environmental_impacts_computer.compute.assert_called_once_with(
            model_active_params=5,
            model_total_params=10,
            model_zone="WOR",
            completion_tokens=100,
            request_latency=20,
        )
        assert result == Usage(
            prompt_tokens=100,
            completion_tokens=100,
            total_tokens=200,
            cost=0.0003,
            impacts=EnvironmentalImpacts(kgCO2eq=1, kWh=2),
        )
