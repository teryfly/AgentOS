"""
Unit tests for MemoryCenter facade.

Tests error handling, degradation, and delegation to internal components.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from agent_os.common import SemanticSearchNotEnabledError
from agent_os.memory_center import MemoryCenter


@pytest.mark.asyncio
class TestMemoryCenterFacade:
    """Tests for MemoryCenter facade methods."""

    @pytest.fixture
    def memory_center(self, memory_config, llm_gateway_config):
        """Create MemoryCenter with mocked storage and injected HTTP client."""
        storage = AsyncMock()
        storage.close = AsyncMock()

        http_client = MagicMock()
        http_client.aclose = AsyncMock()

        center = MemoryCenter(
            storage=storage,
            config=memory_config,
            llm_gateway_config=llm_gateway_config,
            http_client=http_client,
        )
        return center

    async def test_write_failure_does_not_propagate(
        self, memory_center, sample_memory_item
    ):
        """
        Given: Storage write fails
        When: Writing memory
        Then: Exception is caught and logged, not propagated
        """
        memory_center._storage.save.side_effect = Exception("DB error")
        await memory_center.write(sample_memory_item())

    async def test_read_failure_returns_empty_list(self, memory_center):
        """
        Given: Storage read fails
        When: Reading by task
        Then: Empty list is returned (degradation)
        """
        memory_center._storage.query_by_task.side_effect = Exception("DB error")
        result = await memory_center.get_by_task("task-1")
        assert result == []

    async def test_search_failure_returns_empty_list(self, memory_center):
        """
        Given: Storage search fails
        When: Searching by keyword
        Then: Empty list is returned (degradation)
        """
        memory_center._storage.search_keyword.side_effect = Exception("DB error")
        result = await memory_center.search_by_keyword("query")
        assert result == []

    async def test_build_context_failure_returns_minimal_context(
        self, memory_center
    ):
        """
        Given: Context assembly fails
        When: Building context
        Then: Minimal MemoryContext is returned (empty items)
        """
        memory_center._storage.query_by_task.side_effect = Exception("DB error")
        result = await memory_center.build_context("task-1")
        assert result.task_id == "task-1"
        assert result.items == []
        assert result.truncated is False

    async def test_semantic_search_disabled_raises_error(
        self, memory_center
    ):
        """
        Given: Semantic search disabled in config
        When: Attempting semantic search
        Then: SemanticSearchNotEnabledError is raised
        """
        with pytest.raises(SemanticSearchNotEnabledError):
            await memory_center.search_semantic("query")

    async def test_supports_semantic_search_returns_config_value(
        self, memory_center
    ):
        """
        Given: MemoryCenter with config
        When: Checking semantic search support
        Then: Returns config.semantic_search_enabled value
        """
        memory_center._config.semantic_search_enabled = False
        assert memory_center.supports_semantic_search() is False

        memory_center._config.semantic_search_enabled = True
        assert memory_center.supports_semantic_search() is True

    async def test_document_query_empty_ids_returns_empty(
        self, memory_center
    ):
        """
        Given: Empty document_ids list
        When: Querying documents by IDs
        Then: Empty list is returned immediately (no HTTP call)
        """
        result = await memory_center.query_documents_by_ids([])
        assert result == []

    async def test_get_formatted_documents_returns_none_for_empty(
        self, memory_center
    ):
        """
        Given: Empty document_ids list
        When: Getting formatted documents
        Then: None is returned (not empty string)
        """
        result = await memory_center.get_formatted_documents_by_ids([])
        assert result is None

    async def test_get_formatted_documents_returns_none_for_all_failed(
        self, memory_center
    ):
        """
        Given: All document queries fail
        When: Getting formatted documents
        Then: None is returned
        """
        memory_center._document_service.query_by_ids = AsyncMock(return_value=[])
        result = await memory_center.get_formatted_documents_by_ids([1, 2, 3])
        assert result is None

    async def test_get_formatted_documents_returns_formatted_string(
        self, memory_center, mock_document_response
    ):
        """
        Given: Successful document queries
        When: Getting formatted documents
        Then: Formatted string is returned
        """
        memory_center._document_service.query_by_ids = AsyncMock(
            return_value=[mock_document_response(filename="test.md")]
        )

        result = await memory_center.get_formatted_documents_by_ids([1])

        assert result is not None
        assert "## 参考文档" in result
        assert "test.md" in result

    async def test_close_closes_storage_only_when_client_injected(self, memory_center):
        """
        Given: MemoryCenter with injected HTTP client
        When: Closing
        Then: Storage is closed, injected client is NOT closed by MemoryCenter
        """
        await memory_center.close()

        memory_center._storage.close.assert_called_once()
        memory_center._document_service._client.aclose.assert_not_called()