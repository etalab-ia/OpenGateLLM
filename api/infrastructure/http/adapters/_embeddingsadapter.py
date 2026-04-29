from http import HTTPMethod

from api.domain.provider.entities import ProviderFormattedResponse
from api.schemas.embeddings import Embeddings
from api.utils.variables import EndpointRoute

from ._endpointadapter import EndpointAdapter


class EmbeddingsAdapter(EndpointAdapter):
    SOURCE_ENDPOINT = EndpointRoute.EMBEDDINGS
    TARGET_ENDPOINT_ROUTE = "/v1/embeddings"
    TARGET_ENDPOINT_METHOD = HTTPMethod.POST
    # REQUEST_TYPE = CreateEmbeddingsCommand
    RESPONSE_TYPE = Embeddings

    # def compute_prompt_tokens(self, original_request: OriginalModelRequest) -> int:
    #     prompts = []
    #     if isinstance(original_request.body["input"], str):
    #         prompts = [original_request.body["input"]]
    #     else:
    #         for prompt in original_request.body["input"]:
    #             if isinstance(prompt, str):
    #                 prompts.append(prompt)
    #             elif isinstance(prompt, list):
    #                 for item in prompt:
    #                     if isinstance(item, str):
    #                         prompts.append(item)

    #     prompt_tokens = len(self.tokenizer.encode(" ".join(prompts)))

    #     return prompt_tokens

    def compute_completion_tokens(self, formatted_response: ProviderFormattedResponse) -> int:
        return 0
