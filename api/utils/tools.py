from contextvars import ContextVar
import logging

from elasticsearch import AsyncElasticsearch
from pydantic import TypeAdapter
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._documentmanager import DocumentManager
from api.helpers._elasticsearchvectorstore import ElasticsearchVectorStore
from api.helpers.models import ModelRegistry
from api.schemas.core.context import RequestContext
from api.schemas.core.models import RequestContent
from api.schemas.search import ComparisonFilter, CompoundFilter
from api.utils.exceptions import FeatureNotEnabledException

logger = logging.getLogger(__name__)


class SearchTool:
    PROMPT_TEMPLATE = """
Respond to the user's query using only information found in the provided retrieved documents.
- Detect the language of the user's query  and reply in that language.
- Make factual claims only if supported by the retrieved documents. If the answer is not present, clearly state: "I do not know based on the provided documents." in the same language as the user's query.
- If no documents are retrieved, state: "No documents were provided; this answer does not rely on documents." in the same language as the user's query.
- Keep your response concise and clear.

Context:
- User query: {query}
- Retrieved documents:
{chunks}

Output Format:
- Reply in the user's language.
- Attribute each fact to its source by document position (e.g., "According to Document 1: ...").
- If no documents are provided, state: "No documents were provided; this answer does not rely on documents."
- If none of the documents answer the query, state: "I do not know based on the provided documents."
"""

    @staticmethod
    async def call(
        request_content: RequestContent,
        postgres_session: AsyncSession,
        redis_client: AsyncRedis,
        model_registry: ModelRegistry,
        request_context: ContextVar[RequestContext],
        document_manager: DocumentManager,
        elasticsearch_vector_store: ElasticsearchVectorStore | None,
        elasticsearch_client: AsyncElasticsearch | None,
    ) -> RequestContent:
        tools = request_content.json.get("tools", [])
        if tools is None:
            return request_content

        results = []
        search_tool = None

        for i, tool in enumerate(tools):
            if tool.get("type") == "search":
                search_tool = request_content.json["tools"].pop(i)
                search_tool.pop("type")
                break

        if not search_tool:
            return request_content

        messages = request_content.json.get("messages", [])
        if not messages:
            return request_content
        query = messages[-1].get("content")
        if not query:
            return request_content

        if elasticsearch_vector_store is None or elasticsearch_client is None:
            raise FeatureNotEnabledException(detail="Search tool is not enabled because Elasticsearch is not configured.")

        metadata_filters = TypeAdapter(ComparisonFilter | CompoundFilter | None).validate_python(search_tool.get("metadata_filters"))

        results = await document_manager.search_chunks(
            query=query,
            method=search_tool.get("method"),
            limit=search_tool.get("limit"),
            offset=search_tool.get("offset"),
            rff_k=search_tool.get("rff_k"),
            score_threshold=search_tool.get("score_threshold"),
            collection_ids=search_tool.get("collection_ids"),
            document_ids=search_tool.get("document_ids"),
            metadata_filters=metadata_filters,
            model_registry=model_registry,
            request_context=request_context,
            elasticsearch_vector_store=elasticsearch_vector_store,
            elasticsearch_client=elasticsearch_client,
            postgres_session=postgres_session,
            redis_client=redis_client,
        )

        if not results:
            return request_content

        chunks = "\n".join([result.chunk.content for result in results])
        request_content.json["messages"][-1]["content"] = SearchTool.PROMPT_TEMPLATE.format(query=query, chunks=chunks)
        request_content.additional_data["search_results"] = [result.model_dump(mode="json") for result in results]

        return request_content
