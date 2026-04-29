from http import HTTPMethod

from api.domain.chat.entities import ChatCompletion, ChatCompletionChunk
from api.utils.variables import EndpointRoute

from ._endpointadapter import EndpointAdapter


class ChatCompletionsAdapter(EndpointAdapter):
    SOURCE_ENDPOINT = EndpointRoute.CHAT_COMPLETIONS
    TARGET_ENDPOINT_ROUTE = "/v1/chat/completions"
    TARGET_ENDPOINT_METHOD = HTTPMethod.POST
    # REQUEST_TYPE = CreateChatCompletionCommand
    RESPONSE_TYPE = ChatCompletion | ChatCompletionChunk
    # TODO: handle streaming responses

    # def compute_prompt_tokens(self, original_request: OriginalModelRequest) -> int:
    #     prompts = []
    #     for message in original_request.body["messages"]:
    #         if isinstance(message, dict):
    #             prompts.append(message.get("content", ""))
    #         elif isinstance(message, list):
    #             for item in message:
    #                 if isinstance(item, dict):
    #                     if item.get("type", {}) == "text":
    #                         prompts.append(item.get("content", ""))

    #     prompt_tokens = len(self.tokenizer.encode(" ".join(prompts)))

    #     return prompt_tokens
