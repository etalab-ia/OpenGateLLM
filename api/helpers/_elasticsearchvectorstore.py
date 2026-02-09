import hashlib
import logging

from elasticsearch import AsyncElasticsearch, helpers
from elasticsearch.helpers import BulkIndexError

from api.schemas.chunks import Chunk
from api.schemas.core.elasticsearch import ElasticsearchChunk, ElasticsearchIndexLanguage
from api.schemas.search import Search, SearchMethod

logger = logging.getLogger(__name__)


class ElasticsearchVectorStore:
    default_method = SearchMethod.HYBRID

    def __init__(self, index_name: str):
        self.index_name = index_name

    async def setup(
        self,
        client: AsyncElasticsearch,
        index_language: ElasticsearchIndexLanguage,
        number_of_shards: int,
        number_of_replicas: int,
        vector_size: int,
    ) -> None:
        """
        Create the index with the correct settings and mappings.

        Args:
            client: AsyncElasticsearch: The Elasticsearch client
            index_language(ElasticsearchIndexLanguage): The language of the index (dutch, english, french, german, italian, portuguese, spanish, swedish)
            number_of_shards(int): The number of shards for the index
            number_of_replicas(int): The number of replicas for the index
            vector_size(int): The size of the vector to be used for the index
        """

        settings = {
            "number_of_shards": number_of_shards,
            "number_of_replicas": number_of_replicas,
            "similarity": {"default": {"type": "BM25"}},
            "analysis": {
                "filter": {
                    "stop": {"type": "stop", "stopwords": index_language.stopwords},
                    "stemmer": {"type": "stemmer", "language": index_language.stemmer},
                },
                "analyzer": {
                    "content_analyzer": {
                        "tokenizer": "standard",
                        "filter": ["lowercase", "stop", "stemmer"],
                    },
                },
            },
        }
        mappings = {
            "properties": {
                # chunk core properties
                "id": {"type": "integer"},
                "collection_id": {"type": "integer"},
                "document_id": {"type": "integer"},
                "embedding": {"type": "dense_vector", "dims": vector_size, "index": True, "similarity": "cosine"},
                "content": {"type": "text", "analyzer": "content_analyzer"},
                "metadata": {"type": "flattened"},
                "created": {"type": "date"},
            },
        }
        if await client.indices.exists(index=self.index_name):
            logger.info(f"Index {self.index_name} already exists, skipping creation.")
            existing_mapping = await client.indices.get_mapping(index=self.index_name)
            existing_vector_size = existing_mapping[self.index_name]["mappings"]["properties"]["embedding"]["dims"]
            assert existing_vector_size == vector_size, f"Index has incorrect vector size for index {self.index_name} ({existing_vector_size} != {vector_size})"  # fmt: off

            return

        await client.indices.create(index=self.index_name, mappings=mappings, settings=settings)

    async def delete_collection(self, client: AsyncElasticsearch, collection_id: int) -> None:
        query = {
            "bool": {
                "must": [
                    {"term": {"collection_id": collection_id}},
                ]
            }
        }

        await client.delete_by_query(index=self.index_name, body={"query": query})

    async def get_chunk_count(self, client: AsyncElasticsearch, collection_id: int, document_id: int) -> int | None:
        body = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"collection_id": collection_id}},
                        {"term": {"document_id": document_id}},
                    ]
                }
            }
        }
        result = await client.count(index=self.index_name, body=body)
        return result["count"]

    async def delete_document(self, client: AsyncElasticsearch, collection_id: int, document_id: int) -> None:
        query = {
            "bool": {
                "must": [
                    {"term": {"collection_id": collection_id}},
                    {"term": {"document_id": document_id}},
                ]
            }
        }

        await client.delete_by_query(index=self.index_name, body={"query": query})

    async def get_chunks(
        self,
        client: AsyncElasticsearch,
        collection_id: int,
        document_id: int,
        offset: int = 0,
        limit: int = 10,
        chunk_id: int | None = None,
    ) -> list[Chunk]:
        body = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"collection_id": collection_id}},
                        {"term": {"document_id": document_id}},
                    ]
                },
            },
            "_source": {"excludes": ["embedding"]},
        }
        if chunk_id is not None:
            body["query"]["bool"]["must"].append({"term": {"id": chunk_id}})

        results = await client.search(index=self.index_name, body=body, from_=offset, size=limit)
        chunks = [Chunk(**hit["_source"]) for hit in results["hits"]["hits"]]
        chunks = sorted(chunks, key=lambda chunk: chunk.id)

        return chunks

    async def upsert(self, client: AsyncElasticsearch, chunks: list[ElasticsearchChunk]) -> None:
        actions = [
            {
                "_index": self.index_name,
                "_id": hashlib.sha256(f"{chunk.collection_id}|{chunk.document_id}|{chunk.id}".encode()).hexdigest(),
                "_source": chunk.model_dump(),
            }
            for chunk in chunks
        ]

        try:
            await helpers.async_bulk(client=client, actions=actions, index=self.index_name)
        except BulkIndexError:
            raise

    async def search(
        self,
        client: AsyncElasticsearch,
        method: SearchMethod,
        collection_ids: list[int],
        query_prompt: str,
        query_vector: list[float] | None,
        limit: int,
        offset: int,
        rff_k: int | None = 20,
        score_threshold: float = 0.0,
    ) -> list[Search]:
        assert method is SearchMethod.LEXICAL or query_vector, "Query vector must not be None for semantic and hybrid search methods"
        assert rff_k is not None or method is not SearchMethod.HYBRID, "RFF k must not be None for hybrid search method"

        if method == SearchMethod.SEMANTIC:
            searches = await self._semantic_search(
                client=client,
                query_vector=query_vector,
                collection_ids=collection_ids,
                limit=limit,
                offset=offset,
                score_threshold=score_threshold,
            )

        elif method == SearchMethod.LEXICAL:
            searches = await self._lexical_search(
                client=client,
                query_prompt=query_prompt,
                collection_ids=collection_ids,
                limit=limit,
                offset=offset,
                score_threshold=score_threshold,
            )

        else:  # method == SearchMethod.HYBRID
            searches = await self._hybrid_search(
                client=client,
                query_prompt=query_prompt,
                query_vector=query_vector,
                collection_ids=collection_ids,
                limit=limit,
                offset=offset,
                rff_k=rff_k,
            )

        return searches

    async def _lexical_search(
        self,
        client: AsyncElasticsearch,
        query_prompt: str,
        collection_ids: list[int],
        limit: int,
        offset: int,
        score_threshold: float = 0.0,
    ) -> list[Search]:
        body = {
            "query": {
                "bool": {
                    "must": {"multi_match": {"query": query_prompt, "fuzziness": "AUTO"}},
                    "filter": {"terms": {"collection_id": collection_ids}},
                }
            },
            "size": limit,
            "from": offset,
            "_source": {"excludes": ["embedding"]},
        }
        results = await client.search(index=self.index_name, body=body)
        searches = [
            Search(
                method=SearchMethod.LEXICAL.value,
                score=hit["_score"],
                chunk=Chunk(**hit["_source"]),
            )
            for hit in results["hits"]["hits"]
        ]
        searches = [search for search in searches if search.score >= score_threshold]
        searches = sorted(searches, key=lambda x: x.score, reverse=True)[:limit]

        return searches

    async def _semantic_search(
        self,
        client: AsyncElasticsearch,
        query_vector: list[float],
        collection_ids: list[int],
        limit: int,
        offset: int,
        score_threshold: float = 0.0,
    ) -> list[Search]:
        body = {
            "knn": {
                "field": "embedding",
                "query_vector": query_vector,
                "k": limit,
                "num_candidates": max(limit * 10, 100),
                "filter": {"terms": {"collection_id": collection_ids}},
            },
            "size": limit,
            "from": offset,
            "_source": {"excludes": ["embedding"]},
        }

        results = await client.search(index=self.index_name, body=body)
        searches = [
            Search(
                method=SearchMethod.SEMANTIC.value,
                score=hit["_score"],
                chunk=Chunk(**hit["_source"]),
            )
            for hit in results["hits"]["hits"]
        ]
        searches = [search for search in searches if search.score >= score_threshold]
        searches = sorted(searches, key=lambda x: x.score, reverse=True)[:limit]

        return searches

    async def _hybrid_search(
        self,
        client: AsyncElasticsearch,
        query_prompt: str,
        query_vector: list[float],
        collection_ids: list[int],
        limit: int,
        offset: int,
        rff_k: int,
        expansion_factor: int = 2,
    ) -> list[Search]:
        """
        Hybrid search combines lexical and semantic search results using Reciprocal Rank Fusion (RRF).

        Args:
            client: AsyncElasticsearch: The Elasticsearch client
            query_prompt (str): The search prompt
            query_vector (list[float]): The query vector
            collection_ids (list[int]): The collection ids
            offset (int): The offset of the results to return
            limit (int): The number of results to return
            rff_k (int): The constant k in the RRF formula
            expansion_factor (int): The factor that increases the number of results to search in each method before reranking

        Returns:
            A combined list of searches with updated scores
        """
        lexical_searches = await self._lexical_search(
            client=client,
            query_prompt=query_prompt,
            collection_ids=collection_ids,
            limit=int(limit * expansion_factor),
            offset=offset,
        )
        semantic_searches = await self._semantic_search(
            client=client,
            query_vector=query_vector,
            collection_ids=collection_ids,
            limit=int(limit * expansion_factor),
            offset=offset,
        )

        combined_scores = {}
        search_map = {}
        for searches in [lexical_searches, semantic_searches]:
            for rank, search in enumerate(searches):
                chunk_id = search.chunk.document_id + search.chunk.id
                if chunk_id not in combined_scores:
                    combined_scores[chunk_id] = 0
                    search_map[chunk_id] = search
                    search_map[chunk_id].method = SearchMethod.HYBRID
                combined_scores[chunk_id] += 1 / (rff_k + rank + 1)

        ranked_scores = sorted(combined_scores.items(), key=lambda item: item[1], reverse=True)
        reranked_searches = []
        for chunk_id, rrf_score in ranked_scores:
            search = search_map[chunk_id]
            search.score = rrf_score
            reranked_searches.append(search)

        searches = reranked_searches[:limit]

        return searches
