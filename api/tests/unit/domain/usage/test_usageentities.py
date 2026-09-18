from api.domain.usage.entities import EnvironmentalImpacts, Usage


class TestUsageComputeRequestCost:
    def test_compute_request_cost(self):
        result = Usage.compute_request_cost(prompt_tokens=100, completion_tokens=100, cost_prompt_tokens=1.0, cost_completion_tokens=2.0)

        assert result == 0.0003


class TestEnvironmentalImpacts:
    def test_should_round_values_to_six_decimals(self):
        impacts = EnvironmentalImpacts(kWh=1.23456789, kgCO2eq=0.123456789)

        assert impacts.kWh == 1.234568
        assert impacts.kgCO2eq == 0.123457
