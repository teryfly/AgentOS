# agent_os.memory_center

**Version:** v1.0  
**Module Type:** Context & Memory Management Hub

---

## Overview

`agent_os.memory_center` is the unified memory management module for the Agent OS system. It provides:

- **Memory Storage**: Persistent storage for SHORT, LONG, and SHARED memories
- **Context Building**: Assembles memory context for task execution
- **Keyword Search**: Full-text search across memories (task-scoped or cross-task)
- **Document Queries**: Unified entry point for knowledge-base document access
- **Graceful Degradation**: Failures never interrupt main execution flow

---

## Installation

```bash
pip install agent-os-memory-center
```

**Dependencies:**
- `agent-os-common>=1.0.0`
- `asyncpg>=0.29.0`
- `httpx>=0.27.0`

---

## Quick Start

### 1. Environment Setup

Create a `.env` file with required variables:

```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=agent_db
DB_USER=agent_user
DB_PASSWORD=your_password

# Chat Backend Configuration
CHAT_BACKEND_URL=http://localhost:8000/v1
API_KEY=your_api_key
CHAT_BACKEND_PROJECT_ID=67

# Memory Configuration (optional)
MEMORY_MAX_ITEMS=20
MEMORY_SEMANTIC_ENABLED=false
```

### 2. Database Migration

INSTALL PGroonga , a PostgreSQL extension as a high-performance, full-text search engine. see:
https://pgroonga.github.io/install/windows.html

Run the SQL migration script:

```bash
psql -h localhost -U agent_user -d agent_db -f migrations/001_create_memory_tables.sql
```

### 3. Basic Usage

```python
from agent_os.memory_center import create_memory_center_from_env
from agent_os.common import MemoryItem, MemoryType, MemorySource

# Create MemoryCenter from environment
memory_center = create_memory_center_from_env()
await memory_center._storage.initialize()

# Write a memory
memory = MemoryItem(
    task_id="task-001",
    type=MemoryType.SHORT,
    source=MemorySource.ACTOR,
    content={"message": "Hello, world!"},
)
await memory_center.write(memory)

# Build context for a task
context = await memory_center.build_context("task-001")
print(f"Found {len(context.items)} memories")

# Search across tasks
results = await memory_center.search_by_keyword(
    query="Coding Task Document",
    task_id=None,  # Cross-task search
    top_k=5
)

# Query documents
doc_text = await memory_center.get_formatted_documents_by_ids([1, 2, 3])
if doc_text:
    print(doc_text)

# Cleanup
await memory_center.close()
```

---

## Core Concepts

### Memory Types

| Type | Scope | Persistence | Use Case |
|---|---|---|---|
| `SHORT` | Task-scoped | Temporary | Tool results, intermediate state |
| `LONG` | Task-scoped | Permanent | Task summaries, final outputs |
| `SHARED` | Global | Permanent | Cross-task shared knowledge |

### Memory Sources

| Source | Description | Metadata Requirements |
|---|---|---|
| `ACTOR` | Written by Actor | None |
| `TOOL` | Tool execution result | `tool_name` (required) |
| `TASK` | Task completion summary | `role`, `task_id` (required); `has_coding_doc` (if contains Coding Task Document) |
| `SYSTEM` | System events | None |

### Cross-Task Search

Cross-task search (`task_id=None`) enables downstream tasks to retrieve memories from upstream tasks:

```python
# result_router retrieves architect_session_group output
results = await memory_center.search_by_keyword(
    query="Coding Task Document",
    task_id=None,  # Global search
    top_k=3
)

# Filter by metadata
filtered = [
    r for r in results
    if r.source == MemorySource.TASK
    and r.type == MemoryType.LONG
    and r.metadata.get("has_coding_doc") == True
]
```

---

## API Reference

### MemoryCenter

#### Write Operations

```python
async def write(memory: MemoryItem) -> None
async def write_batch(memories: list[MemoryItem]) -> None
```

**Error Handling:** Failures are logged but never propagate.

#### Read Operations

```python
async def get_by_task(
    task_id: str,
    types: list[MemoryType] | None = None
) -> list[MemoryItem]
```

**Error Handling:** Failures return empty list.

#### Search Operations

```python
async def search_by_keyword(
    query: str,
    task_id: str | None = None,
    top_k: int = 5
) -> list[MemoryItem]
```

**Parameters:**
- `task_id`: `None` for cross-task search, or specific task ID for scoped search

**Error Handling:** Failures return empty list.

#### Context Building

```python
async def build_context(
    task_id: str,
    include_shared: bool = True,
    query: str | None = None
) -> MemoryContext
```

**Algorithm:**
1. Fetch SHORT memories (task-scoped)
2. Fetch SHARED memories (if `include_shared=True`)
3. Fetch keyword search results (if `query` provided)
4. Deduplicate by memory_id
5. Sort by priority (SHORT > SHARED > LONG, newest first within each type)
6. Truncate to `max_items_per_context`

**Error Handling:** Failures return minimal context (empty items).

#### Document Operations

```python
async def query_documents_by_ids(document_ids: list[int]) -> list[dict]
async def query_documents(
    filenames: list[str] | None = None,
    category_id: int = 5,
    query: str | None = None
) -> list[dict]

@staticmethod
def format_documents(docs: list[dict]) -> str

async def get_formatted_documents_by_ids(
    document_ids: list[int]
) -> str | None
```

**Note:** `get_formatted_documents_by_ids` returns `None` (not empty string) when:
- `document_ids` is empty
- All document queries fail

This allows LlmGateway to skip document block injection when `None`.

---

## Integration with Other Modules

### AgentRuntime

```python
# Build context before Actor execution
memory_ctx = await memory_center.build_context(
    task_id=task.id,
    include_shared=True,
    query=task.description
)
execution_context.metadata["memory"] = memory_ctx

# Write tool result after execution
await memory_center.write(MemoryItem(
    task_id=task.id,
    type=MemoryType.SHORT,
    source=MemorySource.TOOL,
    content=tool_result.data,
    metadata={"tool_name": tool_result.tool_name}
))

# Write task completion
await memory_center.write(MemoryItem(
    task_id=task.id,
    type=MemoryType.LONG,
    source=MemorySource.TASK,
    content={"task_name": task.name, "result": response.content},
    metadata={
        "role": task.role,
        "task_id": task.id,
        "has_coding_doc": True  # If contains Coding Task Document
    }
))
```

### ContextBuilder

```python
# Fetch and format documents
doc_text = await memory_center.get_formatted_documents_by_ids(doc_ids)
context.metadata["injected_documents"] = doc_text  # May be None
```

### result_router (DeterministicActor)

```python
# Cross-task search for Coding Task Document
items = await memory_center.search_by_keyword(
    query="Coding Task Document",
    task_id=None,  # Cross-task
    top_k=3
)

# Filter by metadata
filtered = [
    i for i in items
    if i.source == MemorySource.TASK
    and i.type == MemoryType.LONG
    and i.metadata.get("has_coding_doc") == True
]
```

---

## Testing

### Run Unit Tests

```bash
pytest agent_os/memory_center/tests/unit -v
```

### Run Integration Tests

```bash
# Ensure test database is set up
bash agent_os/memory_center/migrations/setup_test_db.sh

# Run integration tests
pytest agent_os/memory_center/tests/integration -v
```

### Run All Tests

```bash
pytest agent_os/memory_center/tests -v --cov=agent_os.memory_center
```

---

## Configuration

### MemoryConfig

```python
from agent_os.common import MemoryConfig

config = MemoryConfig(
    max_items_per_context=20,        # Default: 20
    short_memory_ttl_ms=None,        # Not used in MVP
    keyword_search_enabled=True,     # Default: True
    semantic_search_enabled=False,   # Default: False
)
```

### LlmGatewayConfig

```python
from agent_os.common import LlmGatewayConfig

llm_config = LlmGatewayConfig(
    base_url="http://localhost:8000/v1",
    token="your_token",
    project_id=67,
    default_timeout_ms=60000,
    max_retries=2,
    retry_delay_ms=1000,
)
```

---

## Performance Considerations

### Connection Pooling

Default PostgreSQL connection pool settings:
- `min_size=10`
- `max_size=20`
- `command_timeout=30`

Adjust based on:
- Concurrent task execution count
- Average query latency
- Database server capacity

### Full-Text Search

- Uses PostgreSQL GIN indexes for efficient keyword search
- English text search configuration by default
- For Chinese text, install `zhparser` extension and update index

### Document Query Concurrency

- Uses `asyncio.gather` for parallel document requests
- Single document failures don't stop others
- Consider implementing request batching for large document sets

---

## Troubleshooting

### Connection Pool Errors

**Symptom:** `asyncpg.pool.PoolConnectionError`

**Solution:**
- Increase `max_size` in pool configuration
- Check database connection limits
- Verify network connectivity

### Full-Text Search Returns Empty

**Symptom:** `search_by_keyword` returns no results despite matching content

**Solution:**
- Verify GIN index exists: `\di memory_items_content_gin`
- Check text search configuration: `SHOW default_text_search_config;`
- For Chinese text, install zhparser extension

### Document Query Timeout

**Symptom:** `get_formatted_documents_by_ids` returns `None` unexpectedly

**Solution:**
- Check chat_backend availability
- Increase `default_timeout_ms` in LlmGatewayConfig
- Verify network connectivity
- Check document IDs exist in database

---

## Future Enhancements

- **Semantic Search**: Vector embedding + similarity search (requires pgvector)
- **Memory Compression**: Automatic summarization of LONG memories
- **TTL-Based Cleanup**: Automatic expiration of SHORT memories
- **Cross-Task Knowledge Graph**: Relationship tracking between tasks

---

## License

Proprietary - Internal Agent OS Module

## Support

For issues and questions, contact the Agent OS development team.
