from api.domain.model import ModelEnvironmentalImpactsComputer, ModelTokenizer
from api.domain.usage.entities import Usage


class UsageComputer:
    COST_TOKENS_SCALE = 1_000_000  # costs are expressed per million tokens

    def __init__(
        self,
        model_environmental_impacts_computer: ModelEnvironmentalImpactsComputer,
        model_tokenizer: ModelTokenizer,
    ):
        self.model_environmental_impacts_computer = model_environmental_impacts_computer
        self.model_tokenizer = model_tokenizer

    def compute_tokens(self, texts: list[str]) -> int:
        return len(self.model_tokenizer.encode(" ".join(texts).strip()))

    def compute_usage(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        cost_prompt_tokens: float,
        cost_completion_tokens: float,
        latency: int,
        model_active_params: int,
        model_total_params: int,
        model_hosting_zone: str,
    ) -> Usage:
        environmental_impacts = self.model_environmental_impacts_computer.compute(
            model_active_params=model_active_params,
            model_total_params=model_total_params,
            model_zone=model_hosting_zone,
            completion_tokens=completion_tokens,
            request_latency=latency,
        )
        cost = self._compute_cost(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_prompt_tokens=cost_prompt_tokens,
            cost_completion_tokens=cost_completion_tokens,
        )

        return Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost=cost,
            impacts=environmental_impacts,
        )

    @staticmethod
    def _compute_cost(prompt_tokens: int, completion_tokens: int, cost_prompt_tokens: float, cost_completion_tokens: float) -> float:
        return round(
            number=prompt_tokens / UsageComputer.COST_TOKENS_SCALE * cost_prompt_tokens
            + completion_tokens / UsageComputer.COST_TOKENS_SCALE * cost_completion_tokens,
            ndigits=6,
        )
