"""
Pytest configuration with shared fixtures for TaskCenter tests.

Provides async support, test database setup, and reusable mocks.
"""
import pytest
import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Try to import agent_os.common, fallback to mock if not available
try:
    from agent_os.common import Task, TaskStatus, TaskResult
    print("✓ Using real agent_os.common")
except ModuleNotFoundError:
    print("⚠ agent_os.common not found, using mock")
    # Import mock and register it in sys.modules
    from tests.utils import mock_common
    sys.modules['agent_os'] = mock_common
    sys.modules['agent_os.common'] = mock_common
    sys.modules['agent_os.common.interfaces'] = mock_common
    sys.modules['agent_os.common.events'] = mock_common

# Now import TaskCenter components
from agent_os.task_center import TaskCenter, DatabasePool, TaskCenterConfig
from agent_os.task_center.storage import PgTaskStore, PgRuntimeStateStore
from tests.utils.test_db import TestDatabase
from tests.utils.mock_event_bus import MockEventBus


# Configure pytest-asyncio
def pytest_configure(config):
    """Configure pytest with asyncio settings."""
    config.option.asyncio_mode = "auto"


@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for the test session."""
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture(scope="function")
def event_loop(event_loop_policy):
    """Create a new event loop for each test function."""
    loop = event_loop_policy.new_event_loop()
    yield loop
    # Clean up
    try:
        loop.close()
    except Exception:
        pass


def _check_db_sync():
    """
    Synchronously check database availability.
    
    Called during test collection phase (before fixtures are available).
    """
    import asyncpg
    
    async def _check():
        try:
            conn = await asyncpg.connect(
                host=os.getenv("TEST_DB_HOST", "localhost"),
                port=int(os.getenv("TEST_DB_PORT", "5432")),
                database=os.getenv("TEST_DB_NAME", "agent_test_db"),
                user=os.getenv("TEST_DB_USER", "agent_test_user"),
                password=os.getenv("TEST_DB_PASSWORD", "test_password"),
                timeout=3
            )
            await conn.close()
            return True
        except Exception as e:
            print(f"\n⚠ Database connection failed: {e}")
            return False
    
    try:
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(_check())
        loop.close()
        return result
    except Exception as e:
        print(f"\n⚠ Database check error: {e}")
        return False


def pytest_collection_modifyitems(config, items):
    """
    Mark tests that require database.
    
    This runs during collection phase, before any fixtures.
    We need to check database availability here to properly mark tests.
    """
    # Check database availability synchronously
    db_available = _check_db_sync()
    
    if not db_available:
        print("\n" + "=" * 60)
        print("⚠ PostgreSQL test database not available")
        print("=" * 60)
        print("Component and integration tests will be SKIPPED.")
        print("\nTo enable these tests:")
        print("  1. Install PostgreSQL")
        print("  2. Create test database:")
        print("     createdb agent_test_db")
        print("  3. Create user:")
        print("     psql -c \"CREATE USER agent_test_user WITH PASSWORD 'test_password';\"")
        print("  4. Grant privileges:")
        print("     psql -c \"GRANT ALL PRIVILEGES ON DATABASE agent_test_db TO agent_test_user;\"")
        print("=" * 60 + "\n")
        
        skip_db = pytest.mark.skip(reason="Database not available")
        
        for item in items:
            test_path = str(item.fspath)
            if "component" in test_path or "integration" in test_path:
                item.add_marker(skip_db)
    else:
        print("\n✓ Database available - component and integration tests enabled\n")


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator[TestDatabase, None]:
    """
    Function-scoped test database.
    
    Creates connection pool per test, ensures isolation.
    """
    db = TestDatabase()
    await db.initialize()
    yield db
    await db.cleanup()


@pytest.fixture
async def db_pool(test_db: TestDatabase) -> AsyncGenerator[DatabasePool, None]:
    """
    Function-scoped database pool.
    
    Clears all data before each test.
    """
    await test_db.clear_all_data()
    pool = test_db.get_pool()
    yield pool


@pytest.fixture
def mock_event_bus() -> MockEventBus:
    """Mock event bus for unit tests."""
    return MockEventBus()


@pytest.fixture
async def task_store(db_pool: DatabasePool) -> PgTaskStore:
    """PostgreSQL task store."""
    return PgTaskStore(db_pool)


@pytest.fixture
async def runtime_store(db_pool: DatabasePool) -> PgRuntimeStateStore:
    """PostgreSQL runtime state store."""
    return PgRuntimeStateStore(db_pool)


@pytest.fixture
async def task_center(
    task_store: PgTaskStore,
    runtime_store: PgRuntimeStateStore,
    mock_event_bus: MockEventBus,
    db_pool: DatabasePool
) -> AsyncGenerator[TaskCenter, None]:
    """
    Fully configured TaskCenter instance.
    """
    config = TaskCenterConfig(max_depth=5, max_metadata_retries=3, max_runtime_retries=3)
    tc = TaskCenter(task_store, runtime_store, mock_event_bus, db_pool, config)
    await tc.initialize()
    yield tc


@pytest.fixture
def sample_metadata() -> dict:
    """Sample task metadata for tests."""
    return {
        "project_id": 42,
        "root_dir": "/tmp/test_project",
        "required_document_ids": [1, 2, 3]
    }