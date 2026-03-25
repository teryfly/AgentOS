"""
Unit tests for search method detection and fallback logic.

Tests PGroonga detection, built-in fallback, and ILIKE ultimate fallback.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agent_os.common import MemoryType


@pytest.mark.asyncio
class TestSearchMethodDetection:
    """Tests for search method detection during initialization."""

    @pytest.fixture
    def mock_pool(self):
        pool = MagicMock()
        conn = AsyncMock()
        pool.acquire.return_value.__aenter__.return_value = conn
        pool.close = AsyncMock()
        return pool, conn

    async def test_pgroonga_method_detected_when_available(self, mock_pool):
        """
        Given: PostgreSQL with PGroonga extension installed
        When: Initializing storage
        Then: _search_method is set to 'pgroonga'
        """
        from agent_os.memory_center.storage import PostgresMemoryStorage
        
        pool, conn = mock_pool
        conn.fetchval.return_value = 1  # Simulate pgroonga exists
        
        with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = pool
            storage = PostgresMemoryStorage(dsn="postgresql://test")
            await storage.initialize()
            
            try:
                assert storage._search_method == 'pgroonga'
            finally:
                await storage.close()

    async def test_builtin_method_when_pgroonga_unavailable(self, mock_pool):
        """
        Given: PostgreSQL without PGroonga extension
        When: Initializing storage
        Then: _search_method is set to 'builtin'
        """
        from agent_os.memory_center.storage import PostgresMemoryStorage
        
        pool, conn = mock_pool
        conn.fetchval.return_value = None  # Simulate pgroonga does not exist
        
        with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = pool
            storage = PostgresMemoryStorage(dsn="postgresql://test")
            await storage.initialize()
            
            try:
                assert storage._search_method == 'builtin'
            finally:
                await storage.close()


@pytest.mark.asyncio
class TestSearchFallbackBehavior:
    """Tests for search fallback from PGroonga -> built-in -> ILIKE."""

    async def test_search_uses_pgroonga_when_available(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Storage initialized with PGroonga
        When: Searching by keyword
        Then: PGroonga search method is used (no exception)
        """
        # Force PGroonga method
        postgres_storage._search_method = 'pgroonga'
        
        # Save test data
        await postgres_storage.save(
            sample_memory_item(content={"text": "test content"})
        )
        
        # Search should use PGroonga without fallback
        results = await postgres_storage.search_keyword(
            query="test content",
            task_id=None,
            top_k=5
        )
        
        assert isinstance(results, list)

    async def test_search_uses_builtin_when_pgroonga_unavailable(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Storage initialized with built-in method
        When: Searching by keyword
        Then: PostgreSQL built-in search is used
        """
        # Force built-in method
        postgres_storage._search_method = 'builtin'
        
        # Save test data
        await postgres_storage.save(
            sample_memory_item(content={"text": "test content"})
        )
        
        # Search should use built-in method
        results = await postgres_storage.search_keyword(
            query="test",
            task_id=None,
            top_k=5
        )
        
        assert isinstance(results, list)

    async def test_search_falls_back_to_like_on_failure(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Both PGroonga and built-in search fail
        When: Searching by keyword
        Then: Falls back to ILIKE pattern matching
        """
        # Save test data
        await postgres_storage.save(
            sample_memory_item(content={"text": "test content"})
        )
        
        # Mock _search_pgroonga and _search_builtin to raise exception
        with patch.object(
            postgres_storage,
            '_search_pgroonga',
            side_effect=Exception("PGroonga error")
        ):
            with patch.object(
                postgres_storage,
                '_search_builtin',
                side_effect=Exception("Built-in error")
            ):
                # Should fall back to LIKE search
                results = await postgres_storage.search_keyword(
                    query="test",
                    task_id=None,
                    top_k=5
                )
                
                # ILIKE should still work
                assert isinstance(results, list)
                # May return results if LIKE pattern matches

    async def test_like_search_handles_special_sql_characters(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Query with SQL special characters (%, _, etc.)
        When: Falling back to LIKE search
        Then: Characters are handled without SQL injection
        """
        # Save test data
        await postgres_storage.save(
            sample_memory_item(content={"text": "test_value%"})
        )
        
        # Force fallback to LIKE by mocking other methods
        postgres_storage._search_method = 'builtin'
        
        with patch.object(
            postgres_storage,
            '_search_builtin',
            side_effect=Exception("Force fallback")
        ):
            # Should not cause SQL error
            results = await postgres_storage.search_keyword(
                query="test_value%",
                task_id=None,
                top_k=5
            )
            
            assert isinstance(results, list)


@pytest.mark.asyncio
class TestSearchMethodWarnings:
    """Tests for warning logs when PGroonga unavailable."""

    async def test_warning_logged_when_pgroonga_unavailable(self, caplog):
        """
        Given: PostgreSQL without PGroonga
        When: Initializing storage
        Then: Warning is logged about missing PGroonga
        """
        from agent_os.memory_center.storage import PostgresMemoryStorage
        import logging
        
        # Set log level to capture warnings
        caplog.set_level(logging.WARNING)
        
        pool = MagicMock()
        conn = AsyncMock()
        conn.fetchval.return_value = None  # Simulate pgroonga does not exist
        pool.acquire.return_value.__aenter__.return_value = conn
        pool.close = AsyncMock()
        
        with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = pool
            storage = PostgresMemoryStorage(dsn="postgresql://test")
            await storage.initialize()
            
            try:
                # Verify warning was logged
                assert any(
                    "PGroonga not available" in record.message
                    for record in caplog.records
                )
            finally:
                await storage.close()