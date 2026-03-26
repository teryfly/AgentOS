# agent-os-kitbag

Tool Execution Hub for Agent OS - Declarative YAML-based tool registration and multi-protocol execution.

## Features

- **Zero-Code Tool Registration**: Define tools in YAML, auto-loaded at startup
- **Multi-Protocol Support**: Python (direct/generator/async), HTTP (REST), Subprocess (shell)
- **Fail-Safe Execution**: All exceptions captured, callers only receive `ToolResult`
- **Thread-Pool Isolation**: Generator-mode tools run in `ThreadPoolExecutor`
- **Permission Safety**: High-risk tools protected by `allowed_roles` fallback
- **Result Standardization**: Uniform `ToolResult` with `tool_name` + `elapsed_ms`
- **Environment Variable Support**: `${VAR}` substitution in YAML configs

## Installation

```bash
pip install agent-os-kitbag
```

## Quick Start

### 1. Initialize Kitbag

```python
from agent_os.kitbag import Kitbag, YamlToolLoader

# Create instance
kitbag = Kitbag()

# Load tools from YAML directory
loader = YamlToolLoader()
loader.load_from_dir(kitbag, "kitbags/")
```

### 2. Execute Tool

```python
from agent_os.common import ToolCall

# Call a tool
result = kitbag.execute(
    ToolCall(name="search", params={"query": "Python", "top_k": 5})
)

if result.success:
    print(result.data)
else:
    print(f"Error: {result.error}")
```

### 3. Query Tool Schemas

```python
# Get single tool schema
schema = kitbag.get_schema("code_execute")
if schema:
    print(f"{schema.name}: {schema.description}")

# List tools for a role
schemas = kitbag.list_schemas_for_role("programmer")
print(f"Available tools: {[s.name for s in schemas]}")
```

### 4. Check Tool Existence

```python
if not kitbag.exists("unknown_tool"):
    raise ValueError("Tool not found during startup validation")
```

## Architecture

```
Kitbag (Facade)
    ├── ToolExecutor (Pipeline: permission → validate → execute → standardize)
    ├── ParameterValidator (Required/Type/Enum/Default)
    ├── PermissionChecker (allowed_roles safety fallback)
    ├── ResultStandardizer (Normalize to ToolResult)
    └── GeneratorRunner (ThreadPool for generator-mode)

YamlToolLoader
    ├── Recursive scan (*.yaml)
    ├── EnvUtils (${VAR} substitution)
    └── ProtocolAdapter dispatch
         ├── PythonProtocolAdapter → PythonTool
         ├── HttpProtocolAdapter → HttpTool
         └── SubprocessProtocolAdapter → SubprocessTool
```

## Environment Variables

| Variable                  | Description               | Example       |
| ------------------------- | ------------------------- | ------------- |
| `CHAT_BACKEND_HOST`       | chat_backend service host | `localhost`   |
| `CHAT_BACKEND_PORT`       | chat_backend service port | `8000`        |
| `CHAT_BACKEND_TOKEN`      | Bearer auth token         | `sk-test-xxx` |
| `CHAT_BACKEND_PROJECT_ID` | Default project ID        | `41`          |

## Testing

```bash
# Run unit tests
pytest tests/unit/ -v

# Run integration tests
pytest tests/integration/ -v

# Run with coverage
pytest --cov=agent_os.kitbag --cov-report=html
```

## License

MIT
