from api.domain.usage.entities import Usage


class TestUsageEntity:
    def test_compute_request_cost(self):
        result = Usage.compute_request_cost(prompt_tokens=100, completion_tokens=100, cost_prompt_tokens=1.0, cost_completion_tokens=2.0)

        assert result == 0.0003
