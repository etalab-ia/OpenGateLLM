import asyncio
import logging
import time
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._websearchmanager import WebSearchManager
from api.helpers.models.routers._modelrouter import ModelRouter
from api.utils.variables import ENDPOINT__CHAT_COMPLETIONS
from api.utils.prompt_loader import get_prompt_renderer

logger = logging.getLogger(__name__)


class DeepSearchPrompts:
    @staticmethod
    def researcher(num_queries: int, lang: str = "fr") -> str:
        renderer = get_prompt_renderer(lang)
        return renderer.render_macro("researcher", module="deepsearch", num_queries=num_queries)

    @staticmethod
    def evaluator(lang: str = "fr") -> str:
        renderer = get_prompt_renderer(lang)
        return renderer.render_macro("evaluator", module="deepsearch")

    @staticmethod
    def extractor(lang: str = "fr") -> str:
        renderer = get_prompt_renderer(lang)
        return renderer.render_macro("extractor", module="deepsearch")

    @staticmethod
    def analytics(lang: str = "fr") -> str:
        renderer = get_prompt_renderer(lang)
        return renderer.render_macro("analytics", module="deepsearch")

    @staticmethod
    def redactor(lang: str = "fr") -> str:
        renderer = get_prompt_renderer(lang)
        return renderer.render_macro("redactor", module="deepsearch")


class TokenCounter:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    async def update_tokens(self, input_tokens: int, output_tokens: int):
        async with self.lock:
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens

    async def get_totals(self) -> Tuple[int, int]:
        async with self.lock:
            return self.total_input_tokens, self.total_output_tokens


class DeepSearchAgent:
    """Agent dedicated to DeepSearch using WebSearchManager."""

    def __init__(self, model: ModelRouter, web_search_manager: WebSearchManager):
        """Initialize the DeepSearch agent with WebSearchManager."""
        self.model = model
        self.web_search_manager = web_search_manager

    async def deep_search(
        self, prompt: str, session: AsyncSession, k: int = 5, iteration_limit: int = 2, num_queries: int = 2, lang: str = "fr"
    ) -> Tuple[str, List[str], dict]:
        """
        Perform a deep search with WebSearchManager and multiple iterations.
        Returns: (final_response, sources, metadata)
        """
        start_time = time.time()
        aggregated_contexts = []
        aggregated_sources = []
        all_search_queries = []
        iteration = 0
        token_counter = TokenCounter()

        try:
            logger.info(f"Starting deep search for: {prompt}")

            new_search_queries = await self._generate_search_queries(token_counter, prompt, num_queries, lang)

            if not new_search_queries:
                logger.warning("No search queries generated. Using original query.")
                new_search_queries = [prompt]

            all_search_queries.extend(new_search_queries)
            logger.info(f"Initial search queries: {new_search_queries}")

            while iteration < iteration_limit:
                logger.info(f"=== Iteration {iteration + 1} ===")
                iteration_contexts = []

                for search_query in new_search_queries[:num_queries]:
                    logger.info(f"Searching for: {search_query}")

                    web_query = await self.web_search_manager.get_web_query(search_query)
                    logger.info(f"Optimized web query: {web_query}")

                    results = await self.web_search_manager.get_results(web_query, k)
                    logger.info(f"Found {len(results)} results for '{web_query}'")

                    for upload_file in results:
                        url = upload_file.filename.replace(".html", "") if upload_file.filename else "unknown"
                        aggregated_sources.append(url)

                        content = await upload_file.read()
                        if isinstance(content, bytes):
                            content = content.decode("utf-8", errors="ignore")

                        await upload_file.seek(0)

                        context = await self._process_content(token_counter, url, prompt, search_query, content, lang)
                        if context:
                            iteration_contexts.append(context)

                if iteration_contexts:
                    aggregated_contexts.extend(iteration_contexts)
                    logger.info(f"Found {len(iteration_contexts)} useful contexts in iteration {iteration + 1}.")
                else:
                    logger.info(f"No useful context found in iteration {iteration + 1}.")

                if iteration_limit > 1:
                    new_search_queries = await self._get_new_search_queries(token_counter, prompt, all_search_queries, aggregated_contexts, lang)
                else:
                    new_search_queries = []

                if new_search_queries == "[]":
                    logger.info("LLM indicates no additional search is needed.")
                    break
                elif new_search_queries:
                    logger.info(f"New search queries for iteration {iteration + 2}: {new_search_queries}")
                    all_search_queries.extend(new_search_queries)
                else:
                    logger.info("No new search queries provided. Ending search.")
                    break

                iteration += 1

            logger.info("Generating final report...")
            final_report = await self._generate_final_report(token_counter, prompt, aggregated_contexts, lang)

            total_input_tokens, total_output_tokens = await token_counter.get_totals()
            elapsed_time = time.time() - start_time

            metadata = {
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "elapsed_time": elapsed_time,
                "iterations": iteration + 1,
                "total_queries": len(all_search_queries),
                "sources_found": len(aggregated_sources),
            }

            logger.info(f"Search completed in {elapsed_time:.2f} seconds.")
            return final_report, aggregated_sources, metadata

        except Exception as e:
            logger.exception(f"Error during deep search: {e}")
            raise

    async def _generate_search_queries(self, token_counter: TokenCounter, user_query: str, num_queries: int = 2, lang: str = "fr") -> List[str]:
        prompt = DeepSearchPrompts.researcher(num_queries, lang)
        renderer = get_prompt_renderer(lang)
        system_text = renderer.render_macro("system_search", module="deepsearch", lang=lang)
        messages = [
            {"role": "system", "content": system_text},
            {"role": "user", "content": f"User request: {user_query}\n\n{prompt}"},
        ]
        response = await self._call_model_async(token_counter, messages, max_tokens=150)

        if response:
            try:
                search_queries = eval(response)
                if isinstance(search_queries, list):
                    return search_queries
                else:
                    logger.warning(f"LLM did not return a list. Response: {response}")
                    return []
            except Exception as e:
                logger.error(f"Error parsing search queries: {e}\nResponse: {response}")
                return []
        return []

    def _clean_html_content(self, html_content: str) -> str:
        """Clean HTML content to make it readable."""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_content, "html.parser")

            for element in soup(["script", "style", "meta", "link", "noscript", "header", "footer", "aside"]):
                element.decompose()

            text = soup.get_text(separator="\n")
            cleaned_text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
            return cleaned_text
        except ImportError:
            logger.warning("BeautifulSoup not available, using raw content")
            return html_content
        except Exception as e:
            logger.warning(f"Error cleaning HTML: {e}")
            return html_content

    async def _is_content_useful(self, token_counter: TokenCounter, user_query: str, content: str, lang: str = "fr") -> bool:
        if not content:
            return False

        prompt = DeepSearchPrompts.evaluator(lang)
        renderer = get_prompt_renderer(lang)
        system_text = renderer.render_macro("system_evaluator", module="deepsearch", lang=lang)
        messages = [
            {"role": "system", "content": system_text},
            {
                "role": "user",
                "content": f"User query: {user_query}\n\nWeb page excerpt (first 5000 characters):\n{content[:5000]}[...]\n\n{prompt}",
            },
        ]
        response = await self._call_model_async(token_counter, messages, max_tokens=10)
        if response:
            answer = response.strip().lower()
            return "oui" in answer or "yes" in answer
        return False

    async def _extract_relevant_context(
        self, token_counter: TokenCounter, user_query: str, search_query: str, content: str, max_tokens: int = 1024, lang: str = "fr"
    ) -> str:
        if not content:
            return ""

        prompt = DeepSearchPrompts.extractor(lang)
        renderer = get_prompt_renderer(lang)
        system_text = renderer.render_macro("system_extractor", module="deepsearch", lang=lang)
        messages = [
            {"role": "system", "content": system_text},
            {
                "role": "user",
                "content": f"User query: {user_query}\nSearch query: {search_query}\n\nFound context (first 20000 characters):\n{content[:20000]}\n\n{prompt}",
            },
        ]
        response = await self._call_model_async(token_counter, messages, max_tokens=max_tokens)
        if response:
            return response.strip()
        return ""

    async def _process_content(
        self, token_counter: TokenCounter, url: str, user_query: str, search_query: str, content: str, lang: str = "fr"
    ) -> str:
        logger.info(f"Processing content from: {url}")

        cleaned_content = self._clean_html_content(content)

        if not cleaned_content:
            logger.warning(f"No exploitable content for: {url}")
            return ""

        is_useful = await self._is_content_useful(token_counter, user_query, cleaned_content, lang)
        logger.info(f"Content usefulness for {url}: {is_useful}")

        if is_useful:
            context = await self._extract_relevant_context(token_counter, user_query, search_query, cleaned_content, lang=lang)
            if context and context.lower() not in ["<next>", "<suivant>"]:
                logger.info(f"Context extracted from {url} (first 200 characters): {context[:200]}")
                return f"[{url}] {context}"

        return ""

    async def _get_new_search_queries(
        self, token_counter: TokenCounter, user_query: str, previous_search_queries: List[str], all_contexts: List[str], lang: str = "fr"
    ):
        if not all_contexts:
            return await self._generate_search_queries(token_counter, user_query, 2, lang)

        context_combined = "\n".join([f"{context[:1000]} [...]" for context in all_contexts])
        prompt = DeepSearchPrompts.analytics(lang)
        renderer = get_prompt_renderer(lang)
        system_text = renderer.render_macro("system_planner", module="deepsearch", lang=lang)
        messages = [
            {"role": "system", "content": system_text},
            {
                "role": "user",
                "content": f"Relevant context found:\n{context_combined}\n\n{prompt}\nUser request: {user_query}\nPrevious searches already performed: {previous_search_queries}",
            },
        ]
        response = await self._call_model_async(token_counter, messages, max_tokens=100)
        if response:
            cleaned = response.strip()
            logger.info(f"Analytics response: {cleaned}")
            if "[]" in cleaned:
                logger.info("Search completed")
                return "[]"
            try:
                new_queries = eval(cleaned)
                if isinstance(new_queries, list):
                    return new_queries
                else:
                    logger.warning(f"LLM did not return a list for new search queries. Response: {response}")
                    return []
            except Exception as e:
                logger.error(f"Error parsing new search queries: {e}\nResponse: {response}")
                return []
        return []

    async def _generate_final_report(self, token_counter: TokenCounter, user_query: str, all_contexts: List[str], lang: str = "fr") -> str:
        if not all_contexts:
            return (
                "No relevant information found to answer your query."
                if lang == "en"
                else "Aucune information pertinente trouvée pour répondre à votre requête."
            )

        context_combined = "\n".join(all_contexts)
        prompt = DeepSearchPrompts.redactor(lang)
        renderer = get_prompt_renderer(lang)
        system_text = renderer.render_macro("system_talented", module="deepsearch", lang=lang)
        messages = [
            {"role": "system", "content": system_text},
            {
                "role": "user",
                "content": f"User request: {user_query}\n\nRelevant contexts gathered:\n{context_combined}\n\n{prompt}\nReminder:\nUser request: {user_query}",
            },
        ]
        report = await self._call_model_async(token_counter, messages, max_tokens=2048)
        return report or ("Failed to generate report." if lang == "en" else "Échec de génération d'un rapport.")

    async def _call_model_async(self, token_counter: TokenCounter, messages: List[dict], max_tokens: int = 2048) -> Optional[str]:
        await asyncio.sleep(0.1)
        try:
            client = self.model.get_client(endpoint=ENDPOINT__CHAT_COMPLETIONS)
            resp = await client.forward_request(
                method="POST",
                json={
                    "messages": messages,
                    "temperature": 0.1,
                    "max_tokens": max_tokens,
                    "model": self.model,
                },
            )
            if resp.status_code == 200:
                result = resp.json()
                try:
                    answer = result["choices"][0]["message"]["content"]
                    input_tokens = result.get("usage", {}).get("prompt_tokens", 0)
                    output_tokens = result.get("usage", {}).get("completion_tokens", 0)
                    await token_counter.update_tokens(input_tokens, output_tokens)
                    return answer
                except (KeyError, IndexError):
                    logger.error(f"Unexpected model response structure: {result}")
                    return None
            else:
                logger.error(f"Model API error: {resp.status_code} - {resp.text}")
                return None
        except Exception as e:
            logger.error(f"Error calling model: {e}")
            return None
