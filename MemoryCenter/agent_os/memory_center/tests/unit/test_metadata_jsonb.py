"""
Unit tests for metadata JSONB handling.

Tests acceptance criterion #39: Metadata JSONB handling.
"""

import pytest

from agent_os.common import MemorySource, MemoryType


@pytest.mark.asyncio
class TestMetadataJsonb:
    """Tests for PostgreSQL JSONB metadata handling."""

    async def test_metadata_with_nested_objects(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: MemoryItem with nested metadata objects
        When: Saving and retrieving
        Then: Nested structure is preserved
        
        Acceptance Criterion #39
        """
        item = sample_memory_item(
            metadata={
                "role": "architect",
                "config": {
                    "max_depth": 10,
                    "options": ["a", "b", "c"]
                },
                "flags": {
                    "has_coding_doc": True,
                    "requires_review": False
                }
            }
        )

        await postgres_storage.save(item)

        results = await postgres_storage.query_by_task(item.task_id)

        assert len(results) == 1
        assert results[0].metadata["config"]["max_depth"] == 10
        assert results[0].metadata["flags"]["has_coding_doc"] is True

    async def test_metadata_with_array_values(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: MemoryItem with array values in metadata
        When: Saving and retrieving
        Then: Arrays are preserved
        """
        item = sample_memory_item(
            metadata={
                "tags": ["important", "urgent", "review"],
                "participants": ["actor1", "actor2"]
            }
        )

        await postgres_storage.save(item)

        results = await postgres_storage.query_by_task(item.task_id)

        assert len(results) == 1
        assert results[0].metadata["tags"] == ["important", "urgent", "review"]
        assert len(results[0].metadata["participants"]) == 2

    async def test_metadata_with_null_values(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: MemoryItem with null values in metadata
        When: Saving and retrieving
        Then: Null values are preserved
        """
        item = sample_memory_item(
            metadata={
                "optional_field": None,
                "required_field": "value"
            }
        )

        await postgres_storage.save(item)

        results = await postgres_storage.query_by_task(item.task_id)

        assert len(results) == 1
        assert results[0].metadata["optional_field"] is None
        assert results[0].metadata["required_field"] == "value"

    async def test_metadata_with_numeric_values(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: MemoryItem with various numeric types in metadata
        When: Saving and retrieving
        Then: Numeric types are preserved
        """
        item = sample_memory_item(
            metadata={
                "count": 42,
                "ratio": 3.14159,
                "large_number": 9999999999,
                "negative": -123
            }
        )

        await postgres_storage.save(item)

        results = await postgres_storage.query_by_task(item.task_id)

        assert len(results) == 1
        assert results[0].metadata["count"] == 42
        assert abs(results[0].metadata["ratio"] - 3.14159) < 0.0001
        assert results[0].metadata["large_number"] == 9999999999
        assert results[0].metadata["negative"] == -123

    async def test_metadata_with_unicode_characters(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: MemoryItem with Unicode characters in metadata
        When: Saving and retrieving
        Then: Unicode is correctly handled
        """
        item = sample_memory_item(
            metadata={
                "chinese": "中文内容",
                "emoji": "🚀✨",
                "mixed": "Hello 世界 🌍"
            }
        )

        await postgres_storage.save(item)

        results = await postgres_storage.query_by_task(item.task_id)

        assert len(results) == 1
        assert results[0].metadata["chinese"] == "中文内容"
        assert results[0].metadata["emoji"] == "🚀✨"
        assert results[0].metadata["mixed"] == "Hello 世界 🌍"

    async def test_search_filters_by_metadata_in_application_layer(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Multiple memories with different metadata
        When: Searching and filtering by metadata
        Then: Can filter results by metadata fields
        
        Acceptance Criterion #17 (architect→result_router scenario)
        """
        await postgres_storage.save_batch([
            sample_memory_item(
                type_=MemoryType.LONG,
                source=MemorySource.TASK,
                content={"text": "Coding Task Document A"},
                metadata={"role": "architect", "has_coding_doc": True}
            ),
            sample_memory_item(
                type_=MemoryType.LONG,
                source=MemorySource.TASK,
                content={"text": "Coding Task Document B"},
                metadata={"role": "engineer", "has_coding_doc": False}
            ),
        ])

        results = await postgres_storage.search_keyword(
            query="Coding Task Document",
            task_id=None,
            top_k=5
        )

        # Filter in application layer
        filtered = [
            r for r in results
            if r.metadata.get("has_coding_doc") == True
        ]

        assert len(filtered) >= 1
        assert all(r.metadata.get("has_coding_doc") for r in filtered)