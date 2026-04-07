import logging

from api.domain.provider.entities import ProviderCarbonFootprintZone
from api.helpers._usagetokenizer import UsageTokenizer
from api.schemas.usage import Usage
from api.utils.carbon import get_carbon_footprint

from ._exchanges import ModelHttpExchange

logger = logging.getLogger(__name__)


class UsageComputer:
    def __init__(
        self,
        tokenizer: UsageTokenizer,
        model_hosting_zone: ProviderCarbonFootprintZone,
        model_total_params: int | None,
        model_active_params: int | None,
    ):
        self.tokenizer = tokenizer
        self.model_hosting_zone = model_hosting_zone
        self.model_total_params = model_total_params
        self.model_active_params = model_active_params

    def compute(
        self,
        exchange: ModelHttpExchange,
        usage: Usage | None,
        cost_prompt_tokens: float | None,
        cost_completion_tokens: float | None,
    ) -> Usage | None:
        if usage is None:
            return None
        updated_usage = usage
        if exchange.original_request.endpoint in self.tokenizer.USAGE_ENDPOINTS:
            try:
                prompt_tokens = self.tokenizer.get_prompt_tokens(endpoint=exchange.original_request.endpoint, body=exchange.original_request.body)
                completion_tokens = self.tokenizer.get_completion_tokens(
                    endpoint=exchange.original_request.endpoint, response_data=exchange.original_response.data
                )
                total_tokens = prompt_tokens + completion_tokens

                carbon_footprint = get_carbon_footprint(
                    active_params=self.model_active_params,
                    total_params=self.model_total_params,
                    model_zone=self.model_hosting_zone,
                    token_count=total_tokens,
                    request_latency=exchange.original_response.latency,
                )
                cost = round(prompt_tokens / 1000000 * cost_prompt_tokens + completion_tokens / 1000000 * cost_completion_tokens, ndigits=6)  # fmt: off

                updated_usage = updated_usage.model_copy(
                    update={
                        "prompt_tokens": usage.prompt_tokens + prompt_tokens,
                        "completion_tokens": usage.completion_tokens + completion_tokens,
                        "total_tokens": usage.total_tokens + total_tokens,
                        "cost": usage.cost + cost,
                        "carbon": usage.carbon.model_copy(
                            update={
                                "kgCO2eq": usage.carbon.kgCO2eq + carbon_footprint.kgCO2eq,
                                "kWh": usage.carbon.kWh + carbon_footprint.kWh,
                            }
                        ),
                        "requests": usage.requests + 1,
                    }
                )

            except Exception as e:
                logger.exception(msg=f"Failed to compute usage values for endpoint {exchange.original_request.endpoint}: {e}.")

        return updated_usage
