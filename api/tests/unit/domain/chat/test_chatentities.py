from api.domain.chat.entities import ChatCompletion, ChatCompletionChunk, CreateChatCompletionsBody
from api.domain.usage.entities import Usage


def _body(**overrides) -> CreateChatCompletionsBody:
    payload = {"model": "chat-router", "messages": [{"role": "user", "content": "hello"}]}
    payload.update(overrides)
    return CreateChatCompletionsBody(**payload)


class TestCreateChatCompletionsBody:
    def test_should_extract_prompts_from_plain_string_contents(self):
        body = _body(messages=[{"role": "system", "content": "be brief"}, {"role": "user", "content": "hello"}])

        assert body.get_prompts() == ["be brief", "hello"]

    def test_should_extract_prompts_from_typed_content_parts(self):
        body = _body(messages=[{"role": "user", "content": [{"type": "text", "text": "hello"}, {"type": "image_url", "image_url": {"url": "x"}}]}])

        assert body.get_prompts() == ["hello"]

    def test_should_skip_messages_without_textual_content(self):
        body = _body(messages=[{"role": "user", "content": None}, {"role": "user", "content": "hello"}])

        assert body.get_prompts() == ["hello"]

    def test_should_return_the_last_message_as_the_user_query(self):
        body = _body(messages=[{"role": "user", "content": "first"}, {"role": "user", "content": "last"}])

        assert body.get_last_user_query() == "last"

    def test_should_replace_the_last_message_content_without_mutating_the_original(self):
        body = _body(messages=[{"role": "user", "content": "first"}, {"role": "user", "content": "last"}])

        grounded = body.with_last_message_content(content="grounded")

        assert grounded.messages[-1]["content"] == "grounded"
        assert body.messages[-1]["content"] == "last"

    def test_should_pop_the_search_tool_and_keep_the_other_tools(self):
        body = _body(tools=[{"type": "function", "function": {}}, {"type": "search", "limit": 5}])

        stripped, search_arguments = body.pop_search_tool()

        assert search_arguments == {"limit": 5}
        assert stripped.tools == [{"type": "function", "function": {}}]

    def test_should_return_no_search_arguments_when_no_search_tool_is_present(self):
        body = _body(tools=[{"type": "function", "function": {}}])

        stripped, search_arguments = body.pop_search_tool()

        assert search_arguments is None
        assert stripped is body

    def test_should_return_no_search_arguments_when_tools_is_null(self):
        stripped, search_arguments = _body().pop_search_tool()

        assert search_arguments is None
        assert stripped is not None


class TestChatCompletion:
    def test_should_return_content_and_reasoning_as_completions(self):
        completion = ChatCompletion(
            id="chat-1",
            model="chat-router",
            object="chat.completion",
            created=0,
            choices=[{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "answer", "reasoning_content": "because"}}],
        )

        assert completion.get_completions() == ["answer\nbecause"]

    def test_should_return_no_completions_when_there_is_no_choice(self):
        completion = ChatCompletion(id="chat-1", model="chat-router", object="chat.completion", created=0, choices=[])

        assert completion.get_completions() == []

    def test_should_extract_content_from_typed_content_parts(self):
        response = {"choices": [{"message": {"content": [{"type": "text", "text": "answer"}]}}]}

        assert ChatCompletion.extract_response_content(response) == "answer"


class TestChatCompletionChunk:
    def test_should_parse_a_data_chunk(self):
        assert ChatCompletionChunk.parse_chunk('data: {"id": "chat-1"}') == {"id": "chat-1"}

    def test_should_parse_the_done_sentinel(self):
        assert ChatCompletionChunk.parse_chunk("data: [DONE]") == "[DONE]"

    def test_should_return_none_for_a_line_that_is_not_a_data_chunk(self):
        assert ChatCompletionChunk.parse_chunk(": ping") is None

    def test_should_return_none_for_a_malformed_data_chunk(self):
        assert ChatCompletionChunk.parse_chunk("data: {not json") is None

    def test_should_extract_delta_content_and_reasoning(self):
        chunk = {"choices": [{"delta": {"content": "answer", "reasoning_content": "because"}}]}

        assert ChatCompletionChunk.extract_chunk_content(chunk) == "answer\nbecause"

    def test_should_extract_nothing_from_a_chunk_without_choices(self):
        assert ChatCompletionChunk.extract_chunk_content({"choices": []}) == ""

    def test_should_build_a_usage_chunk_that_keeps_the_envelope_and_drops_the_choices(self):
        usage = Usage(prompt_tokens=1, completion_tokens=2, total_tokens=3, cost=0.5)

        chunk = ChatCompletionChunk.build_usage_chunk(
            last_chunk={"object": "chat.completion.chunk", "created": 42, "choices": [{"delta": {"content": "hi"}}]},
            request_id="chat-1",
            model="chat-router",
            usage=usage,
        )

        assert chunk == {
            "object": "chat.completion.chunk",
            "created": 42,
            "choices": [],
            "id": "chat-1",
            "model": "chat-router",
            "usage": usage.model_dump(),
        }
