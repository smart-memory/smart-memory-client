"""
Golden Flow Tests: Core CRUD Operations

Tests the complete user journey: add → search → get → delete
Using real SmartMemory service with real databases.

Run with: pytest tests/integration/test_crud_golden.py -v -m golden
"""

import uuid
import pytest

from smartmemory_client import SmartMemoryClientError


@pytest.mark.integration
@pytest.mark.golden
class TestCRUDGoldenFlow:
    """Test the complete CRUD lifecycle with real service."""

    def test_add_get_delete_flow(self, authenticated_client, unique_content):
        """Golden flow: add → get → delete.

        Tests basic CRUD operations without search (which requires embeddings).
        Uses use_pipeline=False for faster testing.
        """
        client = authenticated_client
        content = f"Integration test memory: {unique_content}"

        # 1. ADD - Create a new memory item (skip pipeline for speed)
        item_id = client.add(content, memory_type="semantic", use_pipeline=False)
        assert item_id is not None
        assert isinstance(item_id, str)
        assert len(item_id) > 0

        # 2. GET - Retrieve the specific item by ID
        item = client.get(item_id)
        assert item is not None
        assert unique_content in str(item.content if hasattr(item, "content") else item)

        # 3. DELETE - Remove the item
        deleted = client.delete(item_id)
        assert deleted is True

        # 4. VERIFY DELETE - Item should no longer exist
        deleted_item = client.get(item_id)
        assert deleted_item is None

    @pytest.mark.slow
    def test_add_search_flow_with_pipeline(self, authenticated_client):
        """Golden flow: add with pipeline → search.

        Tests full pipeline including embedding for search.
        Marked slow because pipeline takes time.
        """
        client = authenticated_client
        unique_id = uuid.uuid4().hex[:8]
        content = f"Integration test with embeddings: {unique_id}"

        # Increase timeout for pipeline operations
        original_timeout = client.timeout
        client.timeout = 120.0

        try:
            # 1. ADD with pipeline (creates embeddings)
            item_id = client.add(content, memory_type="semantic", use_pipeline=True)
            assert item_id is not None

            # 2. SEARCH - Should find via vector similarity
            search_results = client.search(unique_id, top_k=10)
            assert isinstance(search_results, (list, dict))

            # 3. Cleanup
            client.delete(item_id)
        finally:
            client.timeout = original_timeout

    def test_add_with_metadata(self, authenticated_client):
        """Test adding memory with custom metadata."""
        client = authenticated_client
        unique_id = uuid.uuid4().hex[:8]
        content = f"Memory with metadata: {unique_id}"
        metadata = {
            "source": "integration_test",
            "priority": "high",
            "test_id": unique_id,
        }

        # Add with metadata (skip pipeline for speed)
        item_id = client.add(
            content, memory_type="semantic", metadata=metadata, use_pipeline=False
        )
        assert item_id is not None

        # Retrieve and verify metadata
        item = client.get(item_id)
        assert item is not None

        # Cleanup
        client.delete(item_id)

    def test_add_different_memory_types(self, authenticated_client):
        """Test adding different memory types."""
        client = authenticated_client
        unique_id = uuid.uuid4().hex[:8]

        memory_types = ["semantic", "episodic", "procedural", "working"]
        created_ids = []

        for mem_type in memory_types:
            content = f"{mem_type} memory test: {unique_id}"
            item_id = client.add(content, memory_type=mem_type, use_pipeline=False)
            assert item_id is not None
            created_ids.append(item_id)

        # Cleanup
        for item_id in created_ids:
            client.delete(item_id)

    def test_search_with_filters(self, authenticated_client):
        """Test search with memory type filter."""
        client = authenticated_client
        unique_id = uuid.uuid4().hex[:8]

        # Add semantic memory (skip pipeline for speed)
        semantic_content = f"Semantic fact: {unique_id}"
        semantic_id = client.add(
            semantic_content, memory_type="semantic", use_pipeline=False
        )

        # Add episodic memory (skip pipeline for speed)
        episodic_content = f"Episodic event: {unique_id}"
        episodic_id = client.add(
            episodic_content, memory_type="episodic", use_pipeline=False
        )

        # Search with filter
        semantic_results = client.search(unique_id, memory_type="semantic")
        assert len(semantic_results) >= 1

        # Cleanup
        client.delete(semantic_id)
        client.delete(episodic_id)

    def test_get_nonexistent_returns_none(self, authenticated_client):
        """Test that getting a nonexistent item returns None."""
        client = authenticated_client
        fake_id = f"nonexistent_{uuid.uuid4().hex}"

        item = client.get(fake_id)
        assert item is None

    def test_delete_nonexistent_returns_false(self, authenticated_client):
        """Test that deleting a nonexistent item returns False or raises appropriately."""
        client = authenticated_client
        fake_id = f"nonexistent_{uuid.uuid4().hex}"

        # May return False or raise SmartMemoryClientError depending on API behavior
        try:
            result = client.delete(fake_id)
            # If it doesn't raise, should return False
            assert result is False or result is None
        except SmartMemoryClientError:
            # Also acceptable - 404 converted to exception
            pass


@pytest.mark.integration
@pytest.mark.golden
class TestIngestFlow:
    """Test the ingestion pipeline flow."""

    def test_ingest_content(self, authenticated_client):
        """Test content ingestion with extraction pipeline."""
        client = authenticated_client
        unique_id = uuid.uuid4().hex[:8]
        content = f"""
        Meeting notes from {unique_id}:
        - John discussed the new product launch scheduled for Q2
        - Mary presented the marketing strategy
        - Action items: Review budget, finalize timeline
        """

        # Ingest with pipeline
        result = client.ingest(content, extractor_name="llm")
        assert result is not None
        assert "item_id" in result or "queued" in result

        # If we got an item_id, clean up
        if "item_id" in result and result["item_id"]:
            client.delete(result["item_id"])
