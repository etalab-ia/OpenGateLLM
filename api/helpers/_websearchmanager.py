from io import BytesIO
import logging
from typing import List, Optional
from urllib.parse import urlparse

from fastapi import UploadFile
import requests
from starlette.datastructures import Headers

from api.clients.web_search_engine import BaseWebSearchEngineClient as WebSearchEngineClient
from api.helpers.models.routers import ModelRouter
from api.utils.variables import ENDPOINT__CHAT_COMPLETIONS
from api.utils.prompt_loader import get_prompt_renderer

logger = logging.getLogger(__name__)


class WebSearchManager:
    def __init__(
        self,
        web_search_engine: WebSearchEngineClient,
        query_model: ModelRouter,
        limited_domains: Optional[List[str]] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        self.web_search_engine = web_search_engine
        self.query_model = query_model
        self.limited_domains = [] if limited_domains is None else limited_domains
        self.user_agent = user_agent

    async def get_web_query(self, prompt: str) -> str:
        renderer = get_prompt_renderer()
        prompt = renderer.render_macro("query", module="websearch", prompt=prompt)
        client = self.query_model.get_client(endpoint=ENDPOINT__CHAT_COMPLETIONS)
        response = await client.forward_request(
            method="POST",
            json={"messages": [{"role": "user", "content": prompt}], "model": self.query_model.name, "temperature": 0.2, "stream": False},
        )
        query = response.json()["choices"][0]["message"]["content"]

        return query

    async def get_results(self, query: str, k: int) -> List[UploadFile]:
        urls = await self.web_search_engine.search(query=query, k=k)
        results = []
        for url in urls:
            # Parse the URL and extract the hostname
            parsed = urlparse(url)
            domain = parsed.hostname
            if not domain:
                # Skip invalid URLs
                continue

            # Check if the domain is authorized
            if self.limited_domains:
                # Allow exact match or subdomains of allowed domains
                if not any(domain == allowed or domain.endswith(f".{allowed}") for allowed in self.limited_domains):
                    # Skip unauthorized domains
                    continue

            # Fetch the content, skipping on network errors
            try:
                response = requests.get(url=url, headers={"User-Agent": self.user_agent}, timeout=5)
            except requests.RequestException:
                logger.exception("Error fetching URL: %s", url)
                continue

            if response.status_code != 200:
                continue

            file = BytesIO(response.text.encode("utf-8"))
            file = UploadFile(filename=f"{url}.html", file=file, headers=Headers({"content-type": "text/html"}))
            results.append(file)

        return results
