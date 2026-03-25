"""
Verification script for TaskCenter installation.
Run this to check if everything is set up correctly.
"""
import sys
import asyncio
from pathlib import Path
# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
print("=" * 60)
print("TaskCenter Installation Verification")
print("=" * 60)
# Check 1: Python version
print("\n1. Checking Python version...")
if sys.version_info >= (3, 11):
    print(f"   ✓ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
else:
    print(f"   ✗ Python {sys.version_info.major}.{sys.version_info.minor} (requires 3.11+)")
    sys.exit(1)
# Check 2: agent_os.common
print("\n2. Checking agent_os.common...")
try:
    from agent_os.common import Task, TaskStatus
    print("   ✓ agent_os.common available (real package)")
    using_mock = False
except ModuleNotFoundError:
    print("   ⚠ agent_os.common not found, using mock")
    from tests.utils import mock_common
    sys.modules['agent_os'] = mock_common
    sys.modules['agent_os.common'] = mock_common
    using_mock = True
# Check 3: TaskCenter module
print("\n3. Checking agent_os.task_center...")
try:
    from agent_os.task_center import TaskCenter, DatabasePool, TaskCenterConfig
    print("   ✓ TaskCenter module loaded")
except ImportError as e:
    print(f"   ✗ Failed to import TaskCenter: {e}")
    sys.exit(1)
# Check 4: Storage layer
print("\n4. Checking storage layer...")
try:
    from agent_os.task_center.storage import PgTaskStore, PgRuntimeStateStore
    print("   ✓ Storage implementations available")
except ImportError as e:
    print(f"   ✗ Failed to import storage: {e}")
    sys.exit(1)
# Check 5: asyncpg
print("\n5. Checking asyncpg...")
try:
    import asyncpg
    print(f"   ✓ asyncpg {asyncpg.__version__}")
except ImportError:
    print("   ✗ asyncpg not installed")
    print("   Run: pip install asyncpg")
    sys.exit(1)
# Check 6: pytest
print("\n6. Checking pytest...")
try:
    import pytest
    print(f"   ✓ pytest {pytest.__version__}")
except ImportError:
    print("   ⚠ pytest not installed (needed for tests)")
    print("   Run: pip install pytest pytest-asyncio")
# Check 7: Database connection (optional)
print("\n7. Checking database connection...")
async def check_db():
    import os
    try:
        pool = await asyncpg.create_pool(
            host=os.getenv("TEST_DB_HOST", "localhost"),
            port=int(os.getenv("TEST_DB_PORT", "5432")),
            database=os.getenv("TEST_DB_NAME", "agent_test_db"),
            user=os.getenv("TEST_DB_USER", "agent_test_user"),
            password=os.getenv("TEST_DB_PASSWORD", "test_password"),
            min_size=1,
            max_size=2
        )
        await pool.close()
        return True
    except Exception as e:
        return str(e)
try:
    result = asyncio.run(check_db())
    if result is True:
        print("   ✓ Database connection successful")
    else:
        print(f"   ⚠ Database connection failed: {result}")
        print("   Tests requiring database will be skipped")
except Exception as e:
    print(f"   ⚠ Could not check database: {e}")
# Summary
print("\n" + "=" * 60)
print("Summary")
print("=" * 60)
if using_mock:
    print("\n⚠ Using mock agent_os.common")
    print("  For production, install real agent_os.common:")
    print("  pip install agent-os-common")
else:
    print("\n✓ All core components available")
print("\nNext steps:")
print("  1. Set environment variables (see .env.example)")
print("  2. Set up PostgreSQL test database:")
print("     createdb agent_test_db")
print("  3. Run tests:")
print("     pytest tests/unit/ -v")
print("     pytest tests/component/ -v")
print("     pytest tests/integration/ -v")
print("\n" + "=" * 60)