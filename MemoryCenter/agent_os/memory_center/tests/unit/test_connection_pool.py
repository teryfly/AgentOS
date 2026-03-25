"""
Unit tests for connection pool configuration.

Tests pool size settings, timeout configuration, and pool lifecycle.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


@pytest.mark.asyncio
class TestConnectionPoolConfiguration:
    """Tests for PostgreSQL connection pool settings."""

    @pytest.fixture
    def mock_pool(self):
        pool = MagicMock()
        conn = AsyncMock()
        conn.fetchval.return_value = 1  # Simulate pgroonga exists
        pool.acquire.return_value.__aenter__.return_value = conn
        pool.close = AsyncMock()
        return pool

    async def test_default_pool_settings_applied(self, mock_pool):
        """
        Given: PostgresMemoryStorage with default settings
        When: Initializing
        Then: Pool is created with min_size=10, max_size=20
        
        Document 7 acceptance criterion: Connection pool defaults
        """
        from agent_os.memory_center.storage import PostgresMemoryStorage
        
        with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_pool
            storage = PostgresMemoryStorage(dsn="postgresql://test")
            await storage.initialize()
            
            try:
                # Verify pool was created with correct settings
                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args.kwargs
                
                assert call_kwargs['min_size'] == 10
                assert call_kwargs['max_size'] == 20
                assert call_kwargs['command_timeout'] == 30
            finally:
                await storage.close()

    async def test_custom_pool_settings_override_defaults(self, mock_pool):
        """
        Given: Custom pool_kwargs provided
        When: Initializing storage
        Then: Custom settings override defaults
        """
        from agent_os.memory_center.storage import PostgresMemoryStorage
        
        with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_pool
            storage = PostgresMemoryStorage(
                dsn="postgresql://test",
                min_size=5,
                max_size=15,
                command_timeout=60
            )
            await storage.initialize()
            
            try:
                call_kwargs = mock_create.call_args.kwargs
                
                assert call_kwargs['min_size'] == 5
                assert call_kwargs['max_size'] == 15
                assert call_kwargs['command_timeout'] == 60
            finally:
                await storage.close()

    async def test_pool_not_recreated_on_multiple_initialize_calls(self, mock_pool):
        """
        Given: Storage already initialized
        When: Calling initialize() again
        Then: Warning is logged, pool not recreated
        """
        from agent_os.memory_center.storage import PostgresMemoryStorage
        
        with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_pool
            storage = PostgresMemoryStorage(dsn="postgresql://test")
            await storage.initialize()
            
            try:
                # Call initialize again
                with patch('agent_os.memory_center.storage.postgres.logger') as mock_logger:
                    await storage.initialize()
                    
                    # Verify warning was logged
                    mock_logger.warning.assert_called_once()
                    assert "already initialized" in mock_logger.warning.call_args[0][0].lower()
                
                # Pool should only be created once
                assert mock_create.call_count == 1
            finally:
                await storage.close()

    async def test_pool_closed_on_storage_close(self, mock_pool):
        """
        Given: Initialized storage with active pool
        When: Calling close()
        Then: Pool.close() is called
        """
        from agent_os.memory_center.storage import PostgresMemoryStorage
        
        with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_pool
            storage = PostgresMemoryStorage(dsn="postgresql://test")
            await storage.initialize()
            
            await storage.close()
            
            # Verify pool was closed
            mock_pool.close.assert_called_once()
            assert storage._pool is None

    async def test_multiple_close_calls_safe(self, mock_pool):
        """
        Given: Storage already closed
        When: Calling close() again
        Then: No exception is raised
        """
        from agent_os.memory_center.storage import PostgresMemoryStorage
        
        with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_pool
            storage = PostgresMemoryStorage(dsn="postgresql://test")
            await storage.initialize()
            
            await storage.close()
            await storage.close()  # Should not raise exception


@pytest.mark.asyncio
class TestConnectionPoolFailures:
    """Tests for connection pool creation failures."""

    async def test_pool_creation_failure_propagates(self):
        """
        Given: Database connection fails
        When: Initializing storage
        Then: Exception is propagated (fail-fast)
        
        Document 7: Connection pool creation failure should fail-fast
        """
        from agent_os.memory_center.storage import PostgresMemoryStorage
        
        with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("Connection failed")
            storage = PostgresMemoryStorage(dsn="postgresql://test")
            
            with pytest.raises(Exception) as exc_info:
                await storage.initialize()
            
            assert "Connection failed" in str(exc_info.value)

    async def test_invalid_dsn_raises_error_on_initialize(self):
        """
        Given: Invalid DSN format
        When: Initializing storage
        Then: Exception is raised
        """
        from agent_os.memory_center.storage import PostgresMemoryStorage
        
        storage = PostgresMemoryStorage(dsn="invalid-dsn-format")
        
        with pytest.raises(Exception):
            await storage.initialize()