import json

import pytest

from api.domain.chat.entities import ChatCompletion, ChatCompletionChunk, ChatCompletionStreamReader, CreateChatCompletionsBody
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

    @pytest.mark.parametrize("field", ["reasoning_content", "reasoning"])
    def test_should_include_reasoning_in_prompts(self, field):
        body = _body(messages=[{"role": "assistant", "content": "answer", field: "because"}])

        assert body.get_prompts() == ["answer\nbecause"]

    def test_should_extract_a_reasoning_only_prompt(self):
        body = _body(messages=[{"role": "assistant", "content": None, "reasoning": "because"}])

        assert body.get_prompts() == ["because"]

    def test_should_default_parallel_tool_calls_is_undefined(self):
        assert not hasattr(_body(), "parallel_tool_calls")


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

    def test_should_return_reasoning_field_as_completions(self):
        completion = ChatCompletion(
            id="chat-1",
            model="chat-router",
            object="chat.completion",
            created=0,
            choices=[{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "answer", "reasoning": "because"}}],
        )

        assert completion.get_completions() == ["answer\nbecause"]

    def test_should_return_reasoning_only_as_completions(self):
        completion = ChatCompletion(
            id="chat-1",
            model="chat-router",
            object="chat.completion",
            created=0,
            choices=[{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": None, "reasoning": "because"}}],
        )

        assert completion.get_completions() == ["because"]


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

    def test_should_extract_delta_reasoning_field(self):
        chunk = {"choices": [{"delta": {"content": "answer", "reasoning": "because"}}]}

        assert ChatCompletionChunk.extract_chunk_content(chunk) == "answer\nbecause"

    def test_should_extract_reasoning_only_from_a_delta(self):
        chunk = {"choices": [{"delta": {"reasoning": "because"}}]}

        assert ChatCompletionChunk.extract_chunk_content(chunk) == "because"

    def test_should_extract_nothing_from_a_chunk_without_choices(self):
        assert ChatCompletionChunk.extract_chunk_content({"choices": []}) == ""

    def test_should_fall_back_to_valid_fields_when_the_provider_sent_no_parseable_chunk(self):
        chunk = ChatCompletionChunk.build_usage_chunk(last_chunk={}, request_id="chat-1", model="chat-router", usage=Usage())

        assert chunk["object"] == "chat.completion.chunk"
        assert isinstance(chunk["created"], int)
        assert chunk["choices"] == []

    def test_should_build_a_usage_chunk_that_reuses_the_last_chunk_and_drops_the_choices(self):
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


def _stream_reader() -> ChatCompletionStreamReader:
    return ChatCompletionStreamReader(model="chat-router", request_id="req-1")


class TestChatCompletionStreamReader:
    def test_should_relay_a_content_chunk_under_the_router_name_and_the_request_id(self):
        stream_reader = _stream_reader()

        line = stream_reader.read('data: {"id": "chat-1", "model": "provider-internal", "choices": [{"delta": {"content": "hi"}}]}')

        assert json.loads(line.removeprefix("data: ")) == {"id": "req-1", "model": "chat-router", "choices": [{"delta": {"content": "hi"}}]}
        assert stream_reader.delivered_completions == ["hi"]
        assert stream_reader.has_delivered_chunks

    def test_should_relay_and_count_a_content_chunk_whose_text_contains_the_data_prefix(self):
        stream_reader = _stream_reader()

        line = stream_reader.read('data: {"id": "chat-1", "model": "provider-internal", "choices": [{"delta": {"content": "see data: here"}}]}')

        assert json.loads(line.removeprefix("data: ")) == {
            "id": "req-1",
            "model": "chat-router",
            "choices": [{"delta": {"content": "see data: here"}}],
        }
        assert stream_reader.delivered_completions == ["see data: here"]

    def test_should_stop_at_the_done_sentinel_without_relaying_it(self):
        stream_reader = _stream_reader()

        assert stream_reader.read("data: [DONE]") is None
        assert stream_reader.has_reached_stream_end

    def test_should_relay_an_unparseable_line_untouched_without_counting_it_as_delivered(self):
        stream_reader = _stream_reader()

        assert stream_reader.read(": keep-alive") == ": keep-alive"
        assert not stream_reader.has_delivered_chunks

    def test_should_keep_a_usage_only_chunk_from_the_client(self):
        stream_reader = _stream_reader()

        line = stream_reader.read('data: {"choices": [], "usage": {"prompt_tokens": 12, "completion_tokens": 9, "total_tokens": 21}}')

        assert line is None
        assert stream_reader.provider_usage.completion_tokens == 9
        assert not stream_reader.has_delivered_chunks

    def test_should_relay_a_content_chunk_that_also_carries_the_usage(self):
        stream_reader = _stream_reader()

        line = stream_reader.read(
            'data: {"choices": [{"delta": {"content": "hi"}}], "usage": {"prompt_tokens": 12, "completion_tokens": 9, "total_tokens": 21}}'
        )

        assert line is not None
        assert stream_reader.provider_usage.completion_tokens == 9

    def test_should_take_the_first_token_time_from_the_first_chunk_with_content(self):
        stream_reader = _stream_reader()

        stream_reader.read('data: {"choices": [{"delta": {"role": "assistant"}}]}')
        assert stream_reader.first_token_at is None
        stream_reader.read('data: {"choices": [{"delta": {"content": "hi"}}]}')
        first_token_at = stream_reader.first_token_at
        stream_reader.read('data: {"choices": [{"delta": {"content": " there"}}]}')

        assert first_token_at is not None
        assert stream_reader.first_token_at == first_token_at

    def test_should_build_the_usage_line_from_the_last_relayed_chunk(self):
        stream_reader = _stream_reader()
        stream_reader.read('data: {"object": "chat.completion.chunk", "created": 42, "choices": [{"delta": {"content": "hi"}}]}')

        line = stream_reader.build_usage_line(usage=Usage(prompt_tokens=1, completion_tokens=2, total_tokens=3))

        usage_chunk = json.loads(line.removeprefix("data: "))
        assert (usage_chunk["created"], usage_chunk["id"], usage_chunk["model"], usage_chunk["choices"]) == (42, "req-1", "chat-router", [])
        assert usage_chunk["usage"]["completion_tokens"] == 2
