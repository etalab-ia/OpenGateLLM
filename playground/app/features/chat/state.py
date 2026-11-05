import json
from typing import Any

import httpx
import reflex as rx

from app.core.configuration import configuration
from app.features.auth.state import AuthState
from app.features.chat.models import QA, ChatSource
from app.features.collections.models import Collection


class ChatState(AuthState):
    """The main chat state."""

    # List of questions and answers for the chat.
    _messages: list[QA] = []

    # Whether we are processing the question.
    processing: bool = False

    # Sampling parameters
    model: str = ""
    available_models: list[str] = []
    models_loading: bool = False
    temperature: float = 0.7
    top_p: float = 1.0
    max_completion_tokens: int = 1024
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stream: bool = True
    seed_str: str = ""
    stop_sequences: str = ""

    # Retrieval is opt-in; ordinary chat keeps the existing request contract.
    search_enabled: bool = False
    selected_collection_ids: list[int] = []
    available_collections: list[Collection] = []
    collections_loading: bool = False
    collections_error: str = ""
    opengaterag_url: str = configuration.settings.playground_opengaterag_url

    @rx.var
    def selected_collection_count(self) -> int:
        return len(self.selected_collection_ids)

    @rx.event
    def set_search_enabled(self, enabled: bool):
        self.search_enabled = enabled

    @rx.event
    def toggle_collection(self, collection_id: int):
        if collection_id in self.selected_collection_ids:
            self.selected_collection_ids = [selected_id for selected_id in self.selected_collection_ids if selected_id != collection_id]
        else:
            self.selected_collection_ids = [*self.selected_collection_ids, collection_id]

    async def _request_collections(self) -> httpx.Response:
        async with httpx.AsyncClient() as client:
            return await client.get(
                f"{self.opengaterag_url.rstrip('/')}/v1/collections",
                headers={"Authorization": f"Bearer {self.api_key}"},
                params={"offset": 0, "limit": 100, "order_by": "name", "order_direction": "asc"},
                timeout=self.opengatellm_timeout,
            )

    @rx.event
    async def load_collections(self):
        """Refresh accessible collections without resetting the user's selection."""
        if not self.is_authenticated or not self.api_key:
            return

        self.collections_loading = True
        self.collections_error = ""
        yield

        response = None
        try:
            response = await self._request_collections()
            response.raise_for_status()
            collections = [
                Collection(
                    id=item["id"],
                    name=item["name"],
                    description=item.get("description") or "",
                    owner=item.get("owner"),
                    visibility=item.get("visibility") or "private",
                    documents=item.get("documents", 0),
                    size=item.get("size", 0),
                    is_owner=item.get("owner") == self.user_id,
                )
                for item in response.json().get("data", [])
            ]
            self.available_collections = collections
            accessible_ids = {collection.id for collection in collections}
            self.selected_collection_ids = [selected_id for selected_id in self.selected_collection_ids if selected_id in accessible_ids]
        except Exception:
            self.available_collections = []
            detail = None
            if response is not None:
                try:
                    detail = response.json().get("detail")
                except (AttributeError, ValueError):
                    pass
            self.collections_error = detail if isinstance(detail, str) and detail else "Collections could not be loaded. Try again."
        finally:
            self.collections_loading = False
            yield

    @rx.var
    def messages(self) -> list[QA]:
        """Get the list of questions and answers.

        Returns:
            The list of questions and answers.
        """
        return self._messages

    @rx.event
    def clear_chat(self):
        """Clear the chat history."""
        self._messages = []

    @rx.event
    async def load_models(self):
        """Load available models from the API."""
        if not self.is_authenticated or not self.api_key:
            return

        if self.available_models:
            return

        self.models_loading = True
        yield

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.opengatellm_url}/v1/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=self.opengatellm_timeout,
                )
                response.raise_for_status()
                data = response.json()
                models = data.get("data", [])
                models = sorted([model.get("id") for model in models if model.get("type") == "text-generation"])

                if configuration.settings.playground_default_model in models:
                    models.remove(configuration.settings.playground_default_model)
                    models.insert(0, configuration.settings.playground_default_model)

                self.available_models = models
                if not self.model and self.available_models:
                    self.model = self.available_models[0]

        except Exception:
            rx.toast.error("Error loading models.", position="bottom-right")
            self.available_models = []
            self.model = ""
        finally:
            self.models_loading = False
            yield

    # Setters for sampling parameters
    @rx.event
    def set_model(self, model: str):
        """Set the model."""
        self.model = model

    @rx.event
    def set_temperature(self, temperature: float):
        """Set the temperature."""
        self.temperature = temperature

    @rx.event
    def set_top_p(self, top_p: float):
        """Set the top_p."""
        self.top_p = top_p

    @rx.event
    def set_max_completion_tokens(self, max_completion_tokens: int):
        """Set the max_completion_tokens."""
        self.max_completion_tokens = int(max_completion_tokens)

    @rx.event
    def set_frequency_penalty(self, penalty: float):
        """Set the frequency_penalty."""
        self.frequency_penalty = penalty

    @rx.event
    def set_presence_penalty(self, penalty: float):
        """Set the presence_penalty."""
        self.presence_penalty = penalty

    @rx.event
    def set_seed_str(self, seed: str):
        """Set the seed string."""
        self.seed_str = seed

    @rx.event
    def set_stop_sequences(self, sequences: str):
        """Set the stop sequences."""
        self.stop_sequences = sequences

    @staticmethod
    def _source_from_search_result(result: dict[str, Any]) -> ChatSource:
        chunk = result.get("chunk") or {}
        metadata = chunk.get("metadata") or {}

        document_name = ""
        for key in ("source", "document_name", "filename", "name"):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                document_name = value.strip()
                break

        def optional_int(value: Any) -> int | None:
            return value if type(value) is int else None

        document_id = optional_int(chunk.get("document_id"))
        if not document_name:
            document_name = f"Document {document_id}" if document_id is not None else "Unknown document"

        page_number = optional_int(metadata.get("page_number"))
        if page_number is not None and page_number < 1:
            page_number = None

        return ChatSource(
            chunk_id=optional_int(chunk.get("id")),
            collection_id=optional_int(chunk.get("collection_id")),
            document_id=document_id,
            document_name=document_name,
            page_number=page_number,
            content=chunk.get("content") if isinstance(chunk.get("content"), str) else "",
        )

    @staticmethod
    def _merge_sources(existing: list[ChatSource], results: list[dict[str, Any]]) -> list[ChatSource]:
        sources = [*existing]
        seen = {
            (source["chunk_id"], source["collection_id"], source["document_id"], source["document_name"], source["content"]) for source in sources
        }
        for result in results:
            if not isinstance(result, dict):
                continue
            source = ChatState._source_from_search_result(result)
            key = (source["chunk_id"], source["collection_id"], source["document_id"], source["document_name"], source["content"])
            if key not in seen:
                sources.append(source)
                seen.add(key)
        return sources

    def _build_payload(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_completion_tokens": self.max_completion_tokens,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "stream": self.stream,
        }

        if self.search_enabled:
            payload["search"] = True
            payload["search_args"] = {"collection_ids": list(self.selected_collection_ids)}

        if self.seed_str:
            try:
                payload["seed"] = int(self.seed_str)
            except ValueError:
                pass

        if self.stop_sequences:
            stop_list = [sequence.strip() for sequence in self.stop_sequences.split("\n") if sequence.strip()]
            if stop_list:
                payload["stop"] = stop_list

        return payload

    @rx.event
    async def process_question(self, form_data: dict[str, Any]):
        # Get the question from the form
        question = form_data["question"]

        # Check if the question is empty
        if not question:
            return

        async for value in self.api_process_question(question):
            yield value

    @rx.event
    async def api_process_question(self, question: str):
        """Get the response from the API.

        Args:
            question: The user's question.
        """

        # Check if authenticated
        if not self.is_authenticated or not self.api_key:
            return

        if self.search_enabled and not self.selected_collection_ids:
            yield rx.toast.warning("Select at least one collection to search.", position="bottom-right")
            return

        # Add the question to the list of questions.
        qa = QA(question=question, answer="", search_enabled=self.search_enabled, sources_returned=False, sources=[])
        self._messages.append(qa)

        # Clear the input and start the processing.
        self.processing = True
        yield

        # Build the messages.
        messages = []
        for qa in self._messages:
            messages.append({"role": "user", "content": qa["question"]})
            if qa["answer"]:
                messages.append({"role": "assistant", "content": qa["answer"]})

        # Remove the last empty answer.
        if messages and messages[-1]["role"] == "assistant" and not messages[-1]["content"]:
            messages = messages[:-1]

        # Prepare the request payload
        payload = self._build_payload(messages)

        try:
            if self.stream:
                # Streaming response
                async with httpx.AsyncClient() as client:
                    async with client.stream(
                        "POST",
                        f"{self.opengatellm_url}/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                        timeout=self.opengatellm_timeout,
                    ) as response:
                        if response.status_code != 200:
                            error_text = await response.aread()
                            self._messages[-1]["answer"] = f"Error: {error_text.decode()}"
                            self.processing = False
                            yield
                            return

                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data = line[6:]
                                if data == "[DONE]":
                                    break

                                try:
                                    chunk = json.loads(data)
                                except (json.JSONDecodeError, TypeError):
                                    continue
                                if not isinstance(chunk, dict):
                                    continue

                                changed = False
                                if self.search_enabled and isinstance(chunk.get("search_results"), list):
                                    current_sources = self._messages[-1]["sources"]
                                    self._messages[-1]["sources"] = self._merge_sources(current_sources, chunk["search_results"])
                                    self._messages[-1]["sources_returned"] = True
                                    changed = True

                                if chunk.get("choices"):
                                    delta = chunk["choices"][0].get("delta", {})
                                    content = delta.get("content")
                                    if isinstance(content, str) and content:
                                        self._messages[-1]["answer"] += content
                                        changed = True

                                if changed:
                                    self._messages = self._messages
                                    yield
            else:
                # Non-streaming response
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.opengatellm_url}/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                        timeout=self.opengatellm_timeout,
                    )

                    if response.status_code != 200:
                        self._messages[-1]["answer"] = f"Error: {response.text}"
                    else:
                        data = response.json()
                        if self.search_enabled and isinstance(data.get("search_results"), list):
                            self._messages[-1]["sources"] = self._merge_sources([], data["search_results"])
                            self._messages[-1]["sources_returned"] = True
                        if data.get("choices"):
                            content = data["choices"][0]["message"]["content"]
                            self._messages[-1]["answer"] = content

                    yield

        except httpx.TimeoutException:
            self._messages[-1]["answer"] = "Error: Request timeout"
            yield
        except Exception as e:
            self._messages[-1]["answer"] = f"Error: {str(e)}"
            yield

        # Toggle the processing flag.
        self.processing = False
