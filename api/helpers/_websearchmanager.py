from contextvars import ContextVar
from io import BytesIO
import logging
from urllib.parse import urlparse

from fastapi import UploadFile
from redis.asyncio import Redis as AsyncRedis
import requests
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import Headers

from api.clients.web_search_engine import BaseWebSearchEngineClient as WebSearchEngineClient
from api.helpers.models import ModelRegistry
from api.schemas.core.context import RequestContext
from api.utils.variables import ENDPOINT__CHAT_COMPLETIONS

logger = logging.getLogger(__name__)


class WebSearchManager:
    GET_WEB_QUERY_PROMPT = """Tu es un spécialiste pour transformer des demandes en requête google. Tu sais écrire les meilleurs types de recherche pour arriver aux meilleurs résultats.
Voici la demande : {prompt}
Réponds en donnant uniquement une requête Google qui permettrait de trouver des informations pour répondre à la question.

Exemples :
- Question: Peut-on avoir des jours de congé pour un mariage ?
  Réponse: jour de congé mariage conditions

- Question: Donne-moi des informations sur Jules Verne.
  Réponse: Jules Verne

- Question: Comment refaire une pièce d'identité ?
  Réponse: renouvellement pièce identité France

Ne donne pas d'explications, ne mets pas de guillemets, réponds uniquement avec la requête Google qui renverra les meilleurs résultats pour la demande. Ne mets pas de mots qui ne servent à rien dans la requête Google.
"""

    def __init__(
        self,
        web_search_engine: WebSearchEngineClient,
        query_model: str,
        limited_domains: list[str] | None = None,
        user_agent: str | None = None,
    ) -> None:
        self.web_search_engine = web_search_engine
        self.query_model = query_model
        self.limited_domains = [] if limited_domains is None else limited_domains
        self.user_agent = user_agent

    async def get_web_query(
        self,
        prompt: str,
        model_registry: ModelRegistry,
        session: AsyncSession,
        redis_client: AsyncRedis,
        request_context: ContextVar[RequestContext],
    ) -> str:
        model_provider = await model_registry.get_model_provider(
            model=self.query_model,
            endpoint=ENDPOINT__CHAT_COMPLETIONS,
            request_context=request_context,
            session=session,
            redis_client=redis_client,
        )

        prompt = self.GET_WEB_QUERY_PROMPT.format(prompt=prompt)
        response = await model_provider.forward_request(
            method="POST",
            json={"messages": [{"role": "user", "content": prompt}], "model": self.query_model, "temperature": 0.2, "stream": False},
            endpoint=ENDPOINT__CHAT_COMPLETIONS,
            redis_client=redis_client,
        )
        query = response.json()["choices"][0]["message"]["content"]

        return query

    async def get_results(self, query: str, k: int) -> list[UploadFile]:
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
