import logging

from tiktoken.core import Encoding

from api.schemas.chat import ChatCompletion
from api.utils.variables import EndpointRoute

logger = logging.getLogger(__name__)


class ModelTokenizerComputer:
    def __init__(self, tokenizer: Encoding):
        self.tokenizer = tokenizer

    def compute_prompt_tokens(self, endpoint: EndpointRoute, body: dict) -> int:
        match endpoint:
            case EndpointRoute.CHAT_COMPLETIONS:
                # @TODO: add method in ChatCompletion to get prompt tokens
                contents = [message.get("content") for message in body["messages"] if message.get("content")]
                prompt_tokens = sum([len(self.tokenizer.encode(content)) for content in contents])

            case EndpointRoute.EMBEDDINGS:
                # @TODO: add method in EmbeddingsRequest to get prompt tokens
                prompt_tokens = sum([len(self.tokenizer.encode(str(input))) for input in body.get("input", [])])

            case EndpointRoute.RERANK:
                # @TODO: add method in RerankRequest to get prompt tokens
                prompt_tokens = sum([len(self.tokenizer.encode(str(input))) for input in body.get("input", [])])

            case EndpointRoute.SEARCH:
                # @TODO: add method in SearchRequest to get prompt tokens
                prompt_tokens = len(self.tokenizer.encode(str(body.get("prompt", ""))))

            case EndpointRoute.OCR:
                # @TODO: add method in OCRRequest to get prompt tokens
                prompt_tokens = len(self.tokenizer.encode(str(body.get("prompt", ""))))

            case _:
                prompt_tokens = 0

        return prompt_tokens

    def compute_completion_tokens(self, endpoint: EndpointRoute, response_data: dict) -> int:
        match endpoint:
            case EndpointRoute.AUDIO_TRANSCRIPTIONS:
                # @TODO: add audio transcription support (completion tokens)
                return 0
            case EndpointRoute.CHAT_COMPLETIONS:  # streaming responses are handled as a single response (see ModelHttpClient.forward_stream)
                completion_tokens = len(self.tokenizer.encode(ChatCompletion.extract_response_content(response=response_data)))
            case _:
                completion_tokens = 0

        return completion_tokens
