from typing import Any

import httpx
import reflex as rx

from app.core.configuration import configuration
from app.features.auth.state import AuthState
from app.features.chat.models import QA


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
                    timeout=configuration.settings.playground_opengatellm_timeout,
                )
                response.raise_for_status()
                data = response.json()
                models = data.get("data", [])
                models = sorted([model.get("id") for model in models if model.get("type") in ["text-generation", "image-text-to-text"]])

                if configuration.settings.playground_default_model in models:
                    models.remove(configuration.settings.playground_default_model)
                    models.insert(0, configuration.settings.playground_default_model)

                self.available_models = models
                if not self.model and self.available_models:
                    self.model = self.available_models[0]

        except Exception as e:
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
    def set_max_completion_tokens(self, max_tokens: int):
        """Set the max_completion_tokens."""
        self.max_completion_tokens = int(max_tokens)

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

        # Add the question to the list of questions.
        qa = QA(question=question, answer="")
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

        # Add optional parameters
        if self.seed_str:
            try:
                payload["seed"] = int(self.seed_str)
            except ValueError:
                pass

        if self.stop_sequences:
            stop_list = [s.strip() for s in self.stop_sequences.split("\n") if s.strip()]
            if stop_list:
                payload["stop"] = stop_list

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
                        timeout=configuration.settings.playground_opengatellm_timeout,
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
                                    import json

                                    chunk = json.loads(data)
                                    if chunk.get("choices") and len(chunk["choices"]) > 0:
                                        delta = chunk["choices"][0].get("delta", {})
                                        content = delta.get("content")
                                        if content:
                                            self._messages[-1]["answer"] += content
                                            self._messages = self._messages
                                            yield
                                except Exception:
                                    continue
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
                        timeout=configuration.settings.playground_opengatellm_timeout,
                    )

                    if response.status_code != 200:
                        self._messages[-1]["answer"] = f"Error: {response.text}"
                    else:
                        data = response.json()
                        if data.get("choices") and len(data["choices"]) > 0:
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
