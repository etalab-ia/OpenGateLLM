import logging

from elasticsearch import AsyncElasticsearch, helpers
from elasticsearch.helpers import BulkIndexError

from api.clients.vector_store._basevectorstoreclient import BaseVectorStoreClient
from api.schemas.chunks import Chunk
from api.schemas.search import Search, SearchMethod

logger = logging.getLogger(__name__)


class ElasticsearchVectorStoreClient(BaseVectorStoreClient, AsyncElasticsearch):
    default_method = SearchMethod.HYBRID

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        kwargs.pop("type", None)
        self.index_name = kwargs.pop("index_name", None)
        self.index_language = kwargs.pop("index_language", None)
        self.number_of_shards = kwargs.pop("number_of_shards", None)
        self.number_of_replicas = kwargs.pop("number_of_replicas", None)

        AsyncElasticsearch.__init__(self, *args, **kwargs)

    async def setup(self, vector_size: int) -> None:
        """
        Create the index with the correct settings and mappings.

        Args:
            vector_size (int): The size of the vector to be used for the index.
        """

        settings = {
            "number_of_shards": self.number_of_shards,
            "number_of_replicas": self.number_of_replicas,
            "similarity": {"default": {"type": "BM25"}},
            "analysis": {
                "filter": {
                    "stop": {"type": "stop", "stopwords": self.index_language.stopwords},
                    "stemmer": {"type": "stemmer", "language": self.index_language.stemmer},
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
            "dynamic_templates": [
                {"metadata_objects_disabled": {"path_match": "metadata.*", "match_mapping_type": "object", "mapping": {"enabled": False}}},
                {
                    "metadata_dates_by_name": {
                        "path_match": "metadata.*",
                        "match_pattern": "regex",
                        "match": "(?i).*(_at|_date|date)$",
                        "mapping": {
                            "type": "date",
                            "ignore_malformed": True,
                            "format": "strict_date_optional_time||strict_date_time||yyyy-MM-dd'T'HH:mm:ssZ||epoch_millis",
                        },
                    }
                },
                {"metadata_bools": {"path_match": "metadata.*", "match_mapping_type": "boolean", "mapping": {"type": "boolean"}}},
                {
                    "metadata_numbers_long": {
                        "path_match": "metadata.*",
                        "match_mapping_type": "long",
                        "mapping": {"type": "long", "ignore_malformed": True, "coerce": True},
                    }
                },
                {
                    "metadata_numbers_double": {
                        "path_match": "metadata.*",
                        "match_mapping_type": "double",
                        "mapping": {"type": "double", "ignore_malformed": True, "coerce": True},
                    }
                },
                {
                    "metadata_strings": {
                        "path_match": "metadata.*",
                        "match_mapping_type": "string",
                        "mapping": {"type": "keyword", "ignore_above": 1024},
                    }
                },
            ],
            "date_detection": False,
            "numeric_detection": False,
            "properties": {
                "id": {"type": "integer"},
                "collection_id": {"type": "integer"},
                "document_id": {"type": "integer"},
                "embedding": {"type": "dense_vector", "dims": vector_size, "index": True, "similarity": "cosine"},
                "content": {"type": "text", "analyzer": "content_analyzer"},
                "metadata": {"type": "object", "dynamic": True},
                "created": {"type": "date"},
            },
        }

        if await self.indices.exists(index=self.index_name):
            logger.info(f"Index {self.index_name} does not exist, creating index.")
            existing_mapping = await self.indices.get_mapping(index=self.index_name)
            existing_vector_size = existing_mapping[self.index_name]["mappings"]["properties"]["embedding"]["dims"]
            assert existing_vector_size == vector_size, f"Index has incorrect vector size for index {self.index_name} ({existing_vector_size} != {vector_size})"  # fmt: off
            # @TODO: check index UUID in postgres after dynamic creation PR
        else:
            await self.indices.create(index=self.index_name, mappings=mappings, settings=settings)

    async def check(self) -> bool:
        try:
            await self.ping()
            return True
        except Exception:
            return False

    async def close(self) -> None:
        await super(AsyncElasticsearch, self).transport.close()

    async def delete_collection(self, collection_id: int) -> None:
        query = {
            "bool": {
                "must": [
                    {"term": {"collection_id": collection_id}},
                ]
            }
        }

        await self.delete_by_query(index=self.index_name, body={"query": query})

    async def get_chunk_count(self, collection_id: int, document_id: int) -> int | None:
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
        result = await self.count(index=self.index_name, body=body)
        return result["count"]

    async def delete_document(self, collection_id: int, document_id: int) -> None:
        query = {
            "bool": {
                "must": [
                    {"term": {"collection_id": collection_id}},
                    {"term": {"document_id": document_id}},
                ]
            }
        }

        await self.delete_by_query(index=self.index_name, body={"query": query})

    async def get_chunks(self, collection_id: int, document_id: int, offset: int = 0, limit: int = 10, chunk_id: int | None = None) -> list[Chunk]:
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

        results = await self.search(index=self.index_name, body=body, from_=offset, size=limit)
        chunks = []
        for hit in results["hits"]["hits"]:
            chunks.append(
                Chunk(
                    id=hit["_source"]["id"],
                    content=hit["_source"]["content"],
                    metadata=hit["_source"]["metadata"],
                )
            )
        return chunks

    async def upsert(self, collection_id: int, document_id: int, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        actions = [
            {
                "_index": self.index_name,
                "_source": {
                    "id": chunk.id,
                    "collection_id": collection_id,
                    "document_id": document_id,
                    "content": chunk.content,
                    "embedding": embedding,
                    "metadata": chunk.metadata,
                },
            }
            for chunk, embedding in zip(chunks, embeddings)
        ]

        try:
            await helpers.async_bulk(client=self, actions=actions, index=self.index_name)
        except BulkIndexError:
            raise

    async def search(
        self,
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

        if method == SearchMethod.SEMANTIC:
            searches = await self._semantic_search(
                query_vector=query_vector, collection_ids=collection_ids, limit=limit, offset=offset, score_threshold=score_threshold
            )

        elif method == SearchMethod.LEXICAL:
            searches = await self._lexical_search(
                query_prompt=query_prompt, collection_ids=collection_ids, limit=limit, offset=offset, score_threshold=score_threshold
            )

        else:  # method == SearchMethod.HYBRID
            searches = await self._hybrid_search(
                query_prompt=query_prompt, query_vector=query_vector, collection_ids=collection_ids, limit=limit, offset=offset, rff_k=rff_k
            )

        return searches

    async def _lexical_search(
        self, query_prompt: str, collection_ids: list[int], limit: int, offset: int, score_threshold: float = 0.0
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
        results = await AsyncElasticsearch.search(self, index=collection_ids, body=body)
        hits = [hit for hit in results["hits"]["hits"] if hit]
        searches = [
            Search(
                method=SearchMethod.LEXICAL.value,
                score=hit["_score"],
                chunk=Chunk(id=hit["_source"]["id"], content=hit["_source"]["content"], metadata=hit["_source"]["metadata"]),
            )
            for hit in hits
        ]

        searches = [search for search in searches if search.score >= score_threshold]
        searches = sorted(searches, key=lambda x: x.score, reverse=True)[:limit]

        return searches

    async def _semantic_search(
        self, query_vector: list[float], collection_ids: list[int], limit: int, offset: int, score_threshold: float = 0.0
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
        results = await AsyncElasticsearch.search(self, index=collection_ids, body=body)
        hits = [hit for hit in results["hits"]["hits"] if hit]
        searches = [
            Search(
                method=SearchMethod.SEMANTIC.value,
                score=hit["_score"],
                chunk=Chunk(id=hit["_source"]["id"], content=hit["_source"]["content"], metadata=hit["_source"]["metadata"]),
            )
            for hit in hits
        ]

        searches = [search for search in searches if search.score >= score_threshold]
        searches = sorted(searches, key=lambda x: x.score, reverse=True)[:limit]

        return searches

    async def _hybrid_search(
        self, query_prompt: str, query_vector: list[float], collection_ids: list[int], limit: int, offset: int, rff_k: int, expansion_factor: int = 2
    ) -> list[Search]:
        """
        Hybrid search combines lexical and semantic search results using Reciprocal Rank Fusion (RRF).

        Args:
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
            query_prompt=query_prompt,
            collection_ids=collection_ids,
            limit=int(limit * expansion_factor),
            offset=offset,
        )
        semantic_searches = await self._semantic_search(
            query_vector=query_vector,
            collection_ids=collection_ids,
            limit=int(limit * expansion_factor),
            offset=offset,
        )

        combined_scores = {}
        search_map = {}
        for searches in [lexical_searches, semantic_searches]:
            for rank, search in enumerate(searches):
                chunk_id = search.chunk.metadata.get("document_id") + search.chunk.id
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
