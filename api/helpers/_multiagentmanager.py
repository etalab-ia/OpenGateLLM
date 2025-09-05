import asyncio
import logging
import re
from typing import List


from api.helpers.models.routers._modelrouter import ModelRouter
from api.schemas.search import Search
from api.utils.variables import ENDPOINT__CHAT_COMPLETIONS
from api.utils.prompt_loader import get_prompt_renderer

logger = logging.getLogger(__name__)


class MultiAgentManager:
    """Multi Agent manager for handling complex search queries with multiple models.

    Choice sentences are loaded from the prompt renderer when available. If the
    prompt macros are not present, fall back to sensible defaults.
    """

    def __init__(self, synthesis_model: ModelRouter, reranker_model: ModelRouter) -> None:
        """Initialize MultiAgent with the given models."""

        self.synthesis_model = synthesis_model
        self.reranker_model = reranker_model
        renderer = get_prompt_renderer()
        choices = {}
        for i in range(4):
            try:
                # macros are expected to be defined without args and return the sentence
                choices[i] = renderer.render_macro(f"choice_{i}", module="multiagent")
            except Exception as e:
                raise ValueError(f"Prompt macro 'choice_{i}' not found for module 'multiagent' or failed to render: {e}") from e
        self.choices = choices

    async def search(
        self,
        searches: List[Search],
        prompt: str,
    ) -> List[Search]:
        """Multi Agents researcher."""

        async def _go_agents(prompt_text, docs, refs, n_retry=0, max_retry=5, window=5):
            chunk_batch = docs[n_retry * window : (n_retry + 1) * window]
            inputs = [f"(Extrait : {refs[i]}) {chunk}..." for i, chunk in enumerate(chunk_batch)]
            choice = (await self._get_rank(prompt_text, inputs))[0]
            if choice in (0, 3) and n_retry < max_retry:
                return await _go_agents(prompt_text, docs, refs, n_retry + 1)
            if choice in (1, 2):
                return searches, choice, n_retry
            # fallback when max retries reached
            if n_retry >= max_retry:
                return searches, 3, n_retry
            raise ValueError(f"Unknown choice: {choice}")

        initial_docs = [s.chunk.content for s in searches]
        initial_refs = [s.chunk.metadata.get("document_name") for s in searches]
        searches_out, choice, n_retry = await _go_agents(prompt, initial_docs, initial_refs)

        for s in searches_out:
            s.chunk.metadata["choice"] = choice
            s.chunk.metadata["choice_desc"] = self.choices[choice]
            s.chunk.metadata["n_retry"] = n_retry

        return searches_out

    async def full_multiagents(self, searches: List[Search], prompt: str) -> str:
        prompts = self._get_prompts(prompt, searches)
        answers = await self._ask_in_parallel(prompts)
        renderer = get_prompt_renderer()
        return renderer.render_macro("concat", module="multiagent", prompt=prompt, answers=answers)

    def _get_prompts(self, question: str, searches: List[Search]) -> List[str]:
        choice = searches[0].chunk.metadata["choice"]
        renderer = get_prompt_renderer()
        if choice == 1:
            return [renderer.render_macro("teller_1", module="multiagent", doc=s.chunk.content, question=question) for s in searches]
        if choice == 2:
            return [renderer.render_macro("teller_2", module="multiagent", question=question)]
        return []

    async def _get_completion(self, prompt: str, temperature=0.2) -> str:
        client = self.synthesis_model.get_client(endpoint=ENDPOINT__CHAT_COMPLETIONS)
        resp = await client.forward_request(
            method="POST",
            json={"messages": [{"role": "user", "content": prompt}], "temperature": temperature, "max_tokens": 1024, "model": self.synthesis_model},
        )
        return resp.json()["choices"][0]["message"]["content"]

    async def _ask_in_parallel(self, prompts: List[str]) -> List[str]:
        tasks = [asyncio.create_task(self._get_completion(prm, temperature=0.2)) for prm in prompts]
        return await asyncio.gather(*tasks)

    async def _get_rank(self, prompt: str, inputs: List[str]) -> List[int]:
        client = self.reranker_model.get_client(endpoint=ENDPOINT__CHAT_COMPLETIONS)
        renderer = get_prompt_renderer()
        query = renderer.render_macro("choicer", module="multiagent", prompt=prompt, docs=inputs)
        resp = await client.forward_request(
            method="POST",
            json={
                "messages": [{"role": "user", "content": query}],
                "temperature": 0.1,
                "max_tokens": 3,
                "stream": False,
                "model": self.reranker_model,
            },
        )
        text = resp.json()["choices"][0]["message"]["content"]
        m = re.search("[0-3]", text)
        return [int(m.group())] if m else [0]
