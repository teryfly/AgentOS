# TaskCenter - Task State Machine Core for Agent OS

**Version:** 1.0.0

TaskCenter is the task state machine core of the Agent OS framework, responsible for task lifecycle management, dependency graph (DAG) validation, state persistence, and domain event publication.

## Quick Start

### Installation

```bash
# 1. Install agent_os.common (required dependency)
pip install agent-os-common>=1.0.0

# 2. Install TaskCenter in development mode
pip install -e ".[dev]"

# 3. Set up test database
createdb agent_test_db
psql agent_test_db -c "CREATE USER agent_test_user WITH PASSWORD 'test_password';"
psql agent_test_db -c "GRANT ALL PRIVILEGES ON DATABASE agent_test_db TO agent_test_user;"

# 4. Run tests
pytest tests/ -v
```

For detailed installation instructions, see [INSTALL.md](INSTALL.md).

## Architecture Overview

```
┌────────────────────────────────────────────┐
│           TaskCenter (Facade)              │
│     Single async API for all callers       │
├────────────────────────────────────────────┤
│         Business Logic Layer               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │StateMach │  │Lifecycle │  │  Batch   │ │
│  │  ine     │  │ Manager  │  │Processor │ │
│  └──────────┘  └──────────┘  └──────────┘ │
├────────────────────────────────────────────┤
│          Storage Layer (async)             │
│  ┌──────────────────┐  ┌─────────────────┐│
│  │  PgTaskStore     │  │PgRuntimeStore   ││
│  └──────────────────┘  └─────────────────┘│
└────────────────────────────────────────────┘
```

## Core Features

- ✅ **Async-first** - All public APIs are async
- ✅ **Event-driven** - Publishes domain events for coordination
- ✅ **Atomic operations** - DAG mutations in transactions
- ✅ **CAS concurrency** - Optimistic locking with auto-retry
- ✅ **Physical separation** - Fixed metadata vs runtime state
- ✅ **Graph validation** - Cycle detection and depth enforcement


## 初始化代码示例

```python
import asyncio
from agent_os.task_center import TaskCenter, DatabasePool, TaskCenterConfig
from agent_os.task_center.storage import PgTaskStore, PgRuntimeStateStore
from agent_os.common import InMemoryEventBus

async def initialize_task_center():
    # 1. 初始化数据库连接池
    db_pool = DatabasePool()
    await db_pool.initialize()
    
    # 2. 创建存储层
    task_store = PgTaskStore(db_pool)
    runtime_store = PgRuntimeStateStore(db_pool)
    
    # 3. 创建事件总线
    event_bus = InMemoryEventBus()
    
    # 4. 配置
    config = TaskCenterConfig(
        max_depth=10,           # DAG 最大嵌套深度
        max_metadata_retries=3, # 元数据乐观锁重试次数
        max_runtime_retries=3   # 运行时状态乐观锁重试次数
    )
    
    # 5. 创建 TaskCenter
    task_center = TaskCenter(task_store, runtime_store, event_bus, db_pool, config)
    await task_center.initialize()
    
    return task_center, event_bus

# 使用
task_center, event_bus = asyncio.run(initialize_task_center())
```

---

## Usage Example

```python
import asyncio
from agent_os.task_center import TaskCenter, DatabasePool, TaskCenterConfig
from agent_os.task_center.storage import PgTaskStore, PgRuntimeStateStore
from agent_os.common import TaskStatus, TaskResult

async def main():
    # Initialize
    db_pool = DatabasePool()
    await db_pool.initialize()
    
    task_store = PgTaskStore(db_pool)
    runtime_store = PgRuntimeStateStore(db_pool)
    
    from agent_os.common import InMemoryEventBus
    event_bus = InMemoryEventBus()
    
    config = TaskCenterConfig(max_depth=10)
    task_center = TaskCenter(task_store, runtime_store, event_bus, db_pool, config)
    await task_center.initialize()
    
    # Create task
    task = await task_center.create_task(
        name="Example Task",
        description="Process data",
        role="data_processor",
        metadata={"project_id": 42}
    )
    
    # Execute
    await task_center.update_status(task.id, TaskStatus.RUNNING)
    
    # Complete
    result = TaskResult(success=True, data={"output": "processed"}, error=None)
    await task_center.complete_task(task.id, result)
    
    print(f"Task {task.id} completed successfully")

asyncio.run(main())
```

## Public API

### Task Lifecycle

```python
# Create single task
task = await task_center.create_task(name, description, role, depends_on, metadata)

# Create batch atomically
result = await task_center.create_task_batch(items, parent_task_id)

# Status transitions
await task_center.update_status(task_id, TaskStatus.RUNNING)
await task_center.complete_task(task_id, result)
await task_center.fail_task(task_id, error)
await task_center.resume_task(task_id, input_data)
```

### Queries

```python
# Get task
task = await task_center.get_task(task_id)

# List with filters
tasks = await task_center.list_tasks(status=TaskStatus.PENDING, role="coder")

# Get runnable tasks
runnable = await task_center.get_runnable_tasks()
```

### State Management

```python
# Update fixed metadata
await task_center.update_task_metadata(task_id, {"key": "value"})

# Update runtime state (only for RUNNING tasks)
await task_center.update_task_runtime_state(task_id, {"step": 5})

# Query runtime state
state = await task_center.get_task_runtime_state(task_id)
```

## Testing

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/

# Integration tests (requires PostgreSQL)
pytest tests/integration/

# With coverage
pytest --cov=agent_os.task_center --cov-report=html
```

## State Machine

```
PENDING            → RUNNING
RUNNING            → WAITING_INPUT
RUNNING            → WAITING_DEPENDENCY
RUNNING            → COMPLETED
RUNNING            → FAILED
WAITING_INPUT      → RUNNING
WAITING_DEPENDENCY → PENDING
```

Terminal states: `COMPLETED`, `FAILED`

## Domain Events

| Event | Trigger |
|-------|---------|
| `TaskCreated` | Task created |
| `TaskStarted` | Status → RUNNING |
| `TaskCompleted` | Task completes |
| `TaskFailed` | Task fails |
| `TaskWaitingInput` | Status → WAITING_INPUT |
| `TaskWaitingDependency` | Status → WAITING_DEPENDENCY |
| `TaskUnblocked` | Dependency satisfied |
| `TaskResumed` | User input received |

## Configuration

```python
from agent_os.task_center import TaskCenterConfig

config = TaskCenterConfig(
    max_depth=10,                  # Maximum DAG nesting depth
    max_metadata_retries=3,        # Optimistic lock retries for metadata
    max_runtime_retries=3,         # Optimistic lock retries for runtime state
    poll_interval_ms=500           # AgentRuntime polling interval
)
```

## Database Schema

```sql
CREATE TABLE tasks (
    id          UUID PRIMARY KEY,
    name        VARCHAR(255),
    role        VARCHAR(64),
    status      VARCHAR(32),
    depends_on  JSONB,
    children    JSONB,
    result      JSONB,
    metadata    JSONB,
    version     INT,
    ...
);

CREATE TABLE task_runtime_states (
    task_id      UUID PRIMARY KEY,
    runtime_data JSONB,
    version      INT,
    ...
);
```

## Contributing

1. Follow architecture constraints in Document 0 and Document 1
2. All methods must be async
3. Use optimistic locking for updates
4. Publish domain events for state changes
5. Write tests for all new features

## License

Copyright © 2024 Agent OS Team. All rights reserved.
