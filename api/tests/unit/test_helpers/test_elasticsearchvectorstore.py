from unittest.mock import AsyncMock

from pydantic import ValidationError
import pytest

from api.helpers._elasticsearchvectorstore import ElasticsearchVectorStore
from api.schemas.chunks import Chunk
from api.schemas.search import Search, SearchArgs, SearchMethod

# --- SearchArgs.rff_k validation tests ---


class TestSearchArgsRffK:
    """Tests for rff_k field validation in SearchArgs."""

    def test_rff_k_default_value(self):
        """Test that rff_k defaults to 60."""
        args = SearchArgs(collections=[1])
        assert args.rff_k == 60

    def test_rff_k_valid_value(self):
        """Test that a valid rff_k value is accepted."""
        args = SearchArgs(collections=[1], rff_k=20)
        assert args.rff_k == 20

    def test_rff_k_minimum_valid_value(self):
        """Test that rff_k=1 (minimum valid value) is accepted."""
        args = SearchArgs(collections=[1], rff_k=1)
        assert args.rff_k == 1

    def test_rff_k_maximum_valid_value(self):
        """Test that rff_k=16384 (maximum valid value) is accepted."""
        args = SearchArgs(collections=[1], rff_k=16384)
        assert args.rff_k == 16384

    def test_rff_k_zero_is_accepted(self):
        """Test that rff_k=0 is accepted (ge=0 constraint)."""
        args = SearchArgs(collections=[1], rff_k=0)
        assert args.rff_k == 0

    def test_rff_k_negative_raises_validation_error(self):
        """Test that a negative rff_k raises a ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SearchArgs(collections=[1], rff_k=-1)
        assert "rff_k" in str(exc_info.value)

    def test_rff_k_exceeds_maximum_raises_validation_error(self):
        """Test that rff_k exceeding 16384 raises a ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SearchArgs(collections=[1], rff_k=16385)
        assert "rff_k" in str(exc_info.value)


# --- Helpers ---


def _make_chunk(chunk_id: int, document_id: int, collection_id: int = 1) -> Chunk:
    """Helper to create a Chunk instance for tests."""
    return Chunk(
        id=chunk_id,
        collection_id=collection_id,
        document_id=document_id,
        content=f"chunk content {chunk_id}",
        metadata={"key": "value"},
    )


def _make_search(chunk_id: int, document_id: int, score: float, method: SearchMethod = SearchMethod.SEMANTIC) -> Search:
    """Helper to create a Search instance for tests."""
    return Search(
        method=method,
        score=score,
        chunk=_make_chunk(chunk_id=chunk_id, document_id=document_id),
    )


def _make_es_hit(chunk_id: int, document_id: int, collection_id: int = 1, score: float = 1.0) -> dict:
    """Helper to create an Elasticsearch hit dict for tests."""
    return {
        "_score": score,
        "_source": {
            "id": chunk_id,
            "collection_id": collection_id,
            "document_id": document_id,
            "document_name": "test.txt",
            "content": f"chunk content {chunk_id}",
            "metadata": {"key": "value"},
            "created": 1697000000,
        },
    }


# --- ElasticsearchVectorStore.search method tests ---


class TestSearch:
    """Tests for ElasticsearchVectorStore.search dispatch and assertions."""

    @pytest.mark.asyncio
    async def test_search_semantic_dispatches_correctly(self):
        """Test that semantic search is dispatched with the right parameters."""
        store = ElasticsearchVectorStore(index_name="test-index")
        mock_client = AsyncMock()

        mock_client.search = AsyncMock(return_value={"hits": {"hits": [_make_es_hit(1, 10, score=0.95)]}})

        results = await store.search(
            client=mock_client,
            method=SearchMethod.SEMANTIC,
            collection_ids=[1],
            query_prompt="test query",
            query_vector=[0.1, 0.2, 0.3],
            limit=10,
            offset=0,
            rff_k=60,
            score_threshold=0.0,
        )

        assert len(results) == 1
        assert results[0].method == SearchMethod.SEMANTIC

    @pytest.mark.asyncio
    async def test_search_lexical_dispatches_correctly(self):
        """Test that lexical search is dispatched with the right parameters."""
        store = ElasticsearchVectorStore(index_name="test-index")
        mock_client = AsyncMock()

        mock_client.search = AsyncMock(return_value={"hits": {"hits": [_make_es_hit(1, 10, score=5.0)]}})

        results = await store.search(
            client=mock_client,
            method=SearchMethod.LEXICAL,
            collection_ids=[1],
            query_prompt="test query",
            query_vector=None,
            limit=10,
            offset=0,
            rff_k=60,
            score_threshold=0.0,
        )

        assert len(results) == 1
        assert results[0].method == SearchMethod.LEXICAL

    @pytest.mark.asyncio
    async def test_search_hybrid_dispatches_correctly(self):
        """Test that hybrid search is dispatched with the right parameters."""
        store = ElasticsearchVectorStore(index_name="test-index")
        mock_client = AsyncMock()

        mock_client.search = AsyncMock(return_value={"hits": {"hits": [_make_es_hit(1, 10, score=0.9)]}})

        results = await store.search(
            client=mock_client,
            method=SearchMethod.HYBRID,
            collection_ids=[1],
            query_prompt="test query",
            query_vector=[0.1, 0.2, 0.3],
            limit=10,
            offset=0,
            rff_k=60,
            score_threshold=0.0,
        )

        assert len(results) == 1
        assert results[0].method == SearchMethod.HYBRID

    @pytest.mark.asyncio
    async def test_search_semantic_without_vector_raises_assertion(self):
        """Test that semantic search without a query vector raises an AssertionError."""
        store = ElasticsearchVectorStore(index_name="test-index")
        mock_client = AsyncMock()

        with pytest.raises(AssertionError, match="Query vector must not be None"):
            await store.search(
                client=mock_client,
                method=SearchMethod.SEMANTIC,
                collection_ids=[1],
                query_prompt="test query",
                query_vector=None,
                limit=10,
                offset=0,
                rff_k=60,
            )

    @pytest.mark.asyncio
    async def test_search_hybrid_without_vector_raises_assertion(self):
        """Test that hybrid search without a query vector raises an AssertionError."""
        store = ElasticsearchVectorStore(index_name="test-index")
        mock_client = AsyncMock()

        with pytest.raises(AssertionError, match="Query vector must not be None"):
            await store.search(
                client=mock_client,
                method=SearchMethod.HYBRID,
                collection_ids=[1],
                query_prompt="test query",
                query_vector=None,
                limit=10,
                offset=0,
                rff_k=60,
            )

    @pytest.mark.asyncio
    async def test_search_hybrid_without_rff_k_raises_assertion(self):
        """Test that hybrid search with rff_k=None raises an AssertionError."""
        store = ElasticsearchVectorStore(index_name="test-index")
        mock_client = AsyncMock()

        with pytest.raises(AssertionError, match="rff_k must not be None for hybrid search method"):
            await store.search(
                client=mock_client,
                method=SearchMethod.HYBRID,
                collection_ids=[1],
                query_prompt="test query",
                query_vector=[0.1, 0.2, 0.3],
                limit=10,
                offset=0,
                rff_k=None,
            )

    @pytest.mark.asyncio
    async def test_search_lexical_allows_none_vector(self):
        """Test that lexical search works fine with query_vector=None."""
        store = ElasticsearchVectorStore(index_name="test-index")
        mock_client = AsyncMock()

        mock_client.search = AsyncMock(return_value={"hits": {"hits": []}})

        results = await store.search(
            client=mock_client,
            method=SearchMethod.LEXICAL,
            collection_ids=[1],
            query_prompt="test query",
            query_vector=None,
            limit=10,
            offset=0,
            rff_k=None,
        )

        assert results == []


# --- ElasticsearchVectorStore._hybrid_search tests ---


class TestHybridSearch:
    """Tests for the _hybrid_search method and RRF scoring."""

    @pytest.mark.asyncio
    async def test_hybrid_search_combines_results_with_rrf(self):
        """Test that hybrid search combines lexical and semantic results using RRF scores."""
        store = ElasticsearchVectorStore(index_name="test-index")
        mock_client = AsyncMock()

        # First call returns lexical results, second call returns semantic results
        mock_client.search = AsyncMock(
            side_effect=[
                {"hits": {"hits": [_make_es_hit(1, 10, score=5.0), _make_es_hit(2, 10, score=3.0)]}},
                {"hits": {"hits": [_make_es_hit(2, 10, score=0.95), _make_es_hit(3, 10, score=0.80)]}},
            ]
        )

        results = await store._hybrid_search(
            client=mock_client,
            query_prompt="test query",
            query_vector=[0.1, 0.2, 0.3],
            collection_ids=[1],
            limit=10,
            offset=0,
            rff_k=60,
        )

        # chunk_id=2 (doc 10) appears in both -> highest RRF score
        # chunk_id=1 (doc 10) and chunk_id=3 (doc 10) appear in one list each
        assert len(results) == 3

        # Chunk 2 should be first since it appears in both lists
        assert results[0].chunk.id == 2
        assert results[0].method == SearchMethod.HYBRID

        # RRF score for chunk 2: 1/(60+1+1) + 1/(60+0+1) = 1/62 + 1/61
        expected_score_chunk2 = 1 / (60 + 1 + 1) + 1 / (60 + 0 + 1)
        assert abs(results[0].score - expected_score_chunk2) < 1e-10

    @pytest.mark.asyncio
    async def test_hybrid_search_respects_limit(self):
        """Test that hybrid search limits the number of results returned."""
        store = ElasticsearchVectorStore(index_name="test-index")
        mock_client = AsyncMock()

        mock_client.search = AsyncMock(
            side_effect=[
                {"hits": {"hits": [_make_es_hit(1, 10, score=5.0), _make_es_hit(2, 10, score=3.0)]}},
                {"hits": {"hits": [_make_es_hit(3, 10, score=0.95), _make_es_hit(4, 10, score=0.80)]}},
            ]
        )

        results = await store._hybrid_search(
            client=mock_client,
            query_prompt="test query",
            query_vector=[0.1, 0.2, 0.3],
            collection_ids=[1],
            limit=2,
            offset=0,
            rff_k=60,
        )

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_hybrid_search_chunk_id_uses_document_field(self):
        """Test that chunk_id for deduplication uses chunk.document_id (not metadata)."""
        store = ElasticsearchVectorStore(index_name="test-index")
        mock_client = AsyncMock()

        # Same chunk id but different document ids -> should be treated as different chunks
        mock_client.search = AsyncMock(
            side_effect=[
                {"hits": {"hits": [_make_es_hit(1, 10, score=5.0)]}},
                {"hits": {"hits": [_make_es_hit(1, 20, score=0.95)]}},
            ]
        )

        results = await store._hybrid_search(
            client=mock_client,
            query_prompt="test query",
            query_vector=[0.1, 0.2, 0.3],
            collection_ids=[1],
            limit=10,
            offset=0,
            rff_k=60,
        )

        # chunk id=1 with document=10 and chunk id=1 with document=20 are different
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_hybrid_search_deduplicates_same_chunk(self):
        """Test that the same chunk appearing in both searches is deduplicated and its RRF score is combined."""
        store = ElasticsearchVectorStore(index_name="test-index")
        mock_client = AsyncMock()

        # Same chunk (id=1, document=10) appears in both lexical and semantic
        mock_client.search = AsyncMock(
            side_effect=[
                {"hits": {"hits": [_make_es_hit(1, 10, score=5.0)]}},
                {"hits": {"hits": [_make_es_hit(1, 10, score=0.95)]}},
            ]
        )

        results = await store._hybrid_search(
            client=mock_client,
            query_prompt="test query",
            query_vector=[0.1, 0.2, 0.3],
            collection_ids=[1],
            limit=10,
            offset=0,
            rff_k=60,
        )

        assert len(results) == 1
        # RRF score: 1/(60+0+1) + 1/(60+0+1) = 2/61
        expected_score = 2 / (60 + 0 + 1)
        assert abs(results[0].score - expected_score) < 1e-10

    @pytest.mark.asyncio
    async def test_hybrid_search_empty_results(self):
        """Test hybrid search with no results from either method."""
        store = ElasticsearchVectorStore(index_name="test-index")
        mock_client = AsyncMock()

        mock_client.search = AsyncMock(
            side_effect=[
                {"hits": {"hits": []}},
                {"hits": {"hits": []}},
            ]
        )

        results = await store._hybrid_search(
            client=mock_client,
            query_prompt="test query",
            query_vector=[0.1, 0.2, 0.3],
            collection_ids=[1],
            limit=10,
            offset=0,
            rff_k=60,
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_hybrid_search_rrf_score_varies_with_rff_k(self):
        """Test that changing rff_k affects the RRF scores."""
        store = ElasticsearchVectorStore(index_name="test-index")
        mock_client = AsyncMock()

        hits_lexical = {"hits": {"hits": [_make_es_hit(1, 10, score=5.0)]}}
        hits_semantic = {"hits": {"hits": [_make_es_hit(1, 10, score=0.9)]}}

        # Run with rff_k=10
        mock_client.search = AsyncMock(side_effect=[hits_lexical, hits_semantic])
        results_k10 = await store._hybrid_search(
            client=mock_client,
            query_prompt="test",
            query_vector=[0.1],
            collection_ids=[1],
            limit=10,
            offset=0,
            rff_k=10,
        )

        # Run with rff_k=100
        mock_client.search = AsyncMock(side_effect=[hits_lexical, hits_semantic])
        results_k100 = await store._hybrid_search(
            client=mock_client,
            query_prompt="test",
            query_vector=[0.1],
            collection_ids=[1],
            limit=10,
            offset=0,
            rff_k=100,
        )

        # Higher rff_k produces lower scores (more smoothing)
        assert results_k10[0].score > results_k100[0].score

    @pytest.mark.asyncio
    async def test_hybrid_search_sets_method_to_hybrid(self):
        """Test that all results from hybrid search have method set to HYBRID."""
        store = ElasticsearchVectorStore(index_name="test-index")
        mock_client = AsyncMock()

        mock_client.search = AsyncMock(
            side_effect=[
                {"hits": {"hits": [_make_es_hit(1, 10, score=5.0)]}},
                {"hits": {"hits": [_make_es_hit(2, 10, score=0.95)]}},
            ]
        )

        results = await store._hybrid_search(
            client=mock_client,
            query_prompt="test query",
            query_vector=[0.1, 0.2, 0.3],
            collection_ids=[1],
            limit=10,
            offset=0,
            rff_k=60,
        )

        for result in results:
            assert result.method == SearchMethod.HYBRID
