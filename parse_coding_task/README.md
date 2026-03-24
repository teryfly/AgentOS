# Coding Task Document Parser

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-0-success.svg)](https://github.com/agent-os/coding-task-document-parser)

Pure Python parsing library for **Coding Task Documents** with **zero external dependencies** (stdlib only). Extracts structured information from documents produced by architect and engineer agents in the Agent OS framework.

## Features

- ✅ **Zero Dependencies** — Uses only Python standard library
- ✅ **No Exception Propagation** — All errors captured in `parse_warnings`
- ✅ **Auto-Format Detection** — Detects architect/engineer/JSON formats automatically
- ✅ **Last-Match Semantics** — Handles multiple termination lines correctly
- ✅ **Overflow Protection** — Guards against anomalous estimates (N > 1000)
- ✅ **Type-Safe** — Full type hints with Python 3.10+ syntax
- ✅ **Well-Tested** — 75+ tests with >95% coverage

## Installation

### From PyPI (when published)

```bash
pip install coding_task_document_parser
```

### From Source (Development)

```bash
# Clone the repository
git clone https://github.com/teryfly/AgentOS/coding-task-document-parser.git
cd coding_task_document_parser

# Install in editable mode
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

### For Agent OS Framework Integration

In the Agent OS project root:

```bash
pip install -e ./libs/coding_task_document_parser
```

## Quick Start

### Basic Usage

```python
from coding_task_document_parser import CodingTaskDocumentParser

# Parse an architect document
architect_doc = """# Coding Task Document

## Architecture Design
Detailed system design...

End of the Coding Task Document, the estimate code file: 15
"""

result = CodingTaskDocumentParser.parse(architect_doc)

print(f"Estimate: {result.estimate_n}")        # 15
print(f"Source: {result.source_type}")         # "architect"
print(f"Warnings: {result.parse_warnings}")    # []
print(f"Sub-phases: {result.sub_phases}")      # None
```

### Parse Engineer JSON Aggregation

```python
engineer_json = """{
  "sub_phases": [
    {
      "phase": "1.1",
      "title": "Environment Setup",
      "document": "# Coding Task Document - Phase 1.1...",
      "estimate_n": 8
    },
    {
      "phase": "1.2",
      "title": "Core Implementation",
      "document": "# Coding Task Document - Phase 1.2...",
      "estimate_n": 12
    }
  ],
  "total_phases": 2
}"""

result = CodingTaskDocumentParser.parse(engineer_json)

print(f"Total estimate: {result.estimate_n}")           # 20 (8 + 12)
print(f"Sub-phases count: {len(result.sub_phases)}")    # 2
print(f"Phase 1.1 estimate: {result.sub_phases[0].estimate_n}")  # 8
```

### Lightweight Estimate Extraction

```python
# Just get the estimate number (faster)
count = CodingTaskDocumentParser.parse_estimate_count(architect_doc)
print(count)  # 15
```

### Extract from GroupActor Output

```python
# GroupActor FINAL content structure
group_content = {
    "history": [...],
    "final_output": {"sub_phases": [...]},  # or Markdown string
    "shared_context": {},
    "total_rounds": 3
}

# Extract document text
doc_text = CodingTaskDocumentParser.extract_from_group_final_content(group_content)

# Then parse
result = CodingTaskDocumentParser.parse(doc_text)
```

### Collect from Conversation History

```python
history = [
    {
        "round": 0,
        "actor_role": "engineer",
        "content": "# Coding Task Document - Phase 1.1 - Setup\n..."
    },
    {
        "round": 1,
        "actor_role": "engineer",
        "content": "# Coding Task Document - Phase 1.2 - Core\n..."
    }
]

sub_phases = CodingTaskDocumentParser.collect_sub_phases_from_history(history)

for phase in sub_phases:
    print(f"{phase.phase}: {phase.title} ({phase.estimate_n} files)")
```

## API Reference

### `CodingTaskDocumentParser` (Static Methods)

#### `parse(text: str) -> ParseResult`

Main entry point. Auto-detects format and parses document.

**Returns:**
- `ParseResult` with fields:
  - `estimate_n: int` — Total file/step estimate
  - `sub_phases: list[SubPhase] | None` — Sub-phases for engineer JSON
  - `raw_document: str` — Document without termination line
  - `source_type: Literal["architect", "engineer"]` — Detected format
  - `parse_warnings: list[str]` — Non-fatal warnings

**Never raises exceptions.** All errors captured in `parse_warnings`.

#### `parse_estimate_count(text: str) -> int`

Lightweight method to extract only the estimate number.

**Returns:** Integer estimate (0 if parse fails).

#### `extract_from_group_final_content(content: dict) -> str`

Extract document text from GroupActor FINAL content dict.

**Priority order:**
1. `final_output` is dict with `sub_phases` → JSON string
2. `final_output` is string with "Coding Task Document" → return as-is
3. Fallback to history scanning → JSON string if found
4. Final fallback → empty string

#### `collect_sub_phases_from_history(history: list[dict]) -> list[SubPhase] | None`

Scan conversation history to reconstruct sub-phase documents.

**Returns:** List of `SubPhase` instances, or `None` if no valid sub-phases found.

### Data Models

#### `ParseResult`

```python
@dataclass
class ParseResult:
    estimate_n: int                                   # Total estimate
    sub_phases: list[SubPhase] | None                # Sub-phases or None
    raw_document: str                                 # Cleaned document text
    source_type: Literal["architect", "engineer"]    # Format type
    parse_warnings: list[str]                        # Warnings list
```

#### `SubPhase`

```python
@dataclass
class SubPhase:
    phase: str          # "1.1", "2.3"
    title: str          # Sub-phase title
    document: str       # Full sub-phase Markdown
    estimate_n: int     # Per-phase estimate
```

## Document Formats

### Architect Format

```markdown
# Coding Task Document

## Architecture Design
...

## Modular Structure
...

End of the Coding Task Document, the estimate code file: 15
```

**Characteristics:**
- Single unified document
- One termination line at the end
- `source_type = "architect"`
- `sub_phases = None`

### Engineer Sub-phase Format

```markdown
# Coding Task Document - Phase 1.1 - Environment Setup

## Objective
...

## Implementation Steps
...

End of the Coding Task Document - Phase 1.1, the estimate code file: 8
```

**Characteristics:**
- Contains phase number in heading
- Phase-specific termination line
- `source_type = "engineer"`
- `sub_phases = None` (single sub-phase)

### Engineer JSON Aggregation Format

```json
{
  "sub_phases": [
    {
      "phase": "1.1",
      "title": "Environment Setup",
      "document": "# Coding Task Document - Phase 1.1...",
      "estimate_n": 8
    },
    {
      "phase": "1.2",
      "title": "Core Implementation",
      "document": "# Coding Task Document - Phase 1.2...",
      "estimate_n": 12
    }
  ],
  "total_phases": 2
}
```

**Characteristics:**
- Multiple sub-phases in JSON array
- `estimate_n` is sum of all sub-phase estimates
- `source_type = "engineer"`
- `sub_phases = [SubPhase, ...]` (list populated)

## Error Handling

### No-Throw Guarantee

This library **never raises exceptions**. All errors are captured in `parse_warnings`.

```python
# Parse invalid JSON
result = CodingTaskDocumentParser.parse('{"invalid json}')

print(result.estimate_n)         # 0
print(result.parse_warnings)     # ["JSON decode error: ..."]
print(result.source_type)        # "architect" (fallback)
```

### Common Scenarios

| Scenario | `estimate_n` | `parse_warnings` |
|----------|--------------|------------------|
| Valid document | N (positive int) | `[]` |
| No termination line | `0` | `["No termination line found"]` |
| N > 1000 (overflow) | `0` | `["Estimate N exceeds 1000..."]` |
| Invalid JSON | `0` | `["JSON decode error: ..."]` |
| Empty input | `0` | `["Empty input text"]` |
| Missing required fields | `0` or partial | Field-specific warnings |

### Checking Parse Success

```python
result = CodingTaskDocumentParser.parse(text)

if result.estimate_n > 0 and not result.parse_warnings:
    print("✓ Parse successful")
elif result.estimate_n > 0 and result.parse_warnings:
    print("⚠ Parse succeeded with warnings")
    for warning in result.parse_warnings:
        print(f"  - {warning}")
else:
    print("✗ Parse failed")
    for warning in result.parse_warnings:
        print(f"  - {warning}")
```

## Integration with Agent OS Framework

### Kitbag Tool Registration

This library is accessed **exclusively through the Kitbag tool** in Agent OS. Direct imports are prohibited in Actor code.

**YAML Tool Definition** (`kitbags/python/coding_task_document_parser.yaml`):

```yaml
protocol: python

tools:
  - name: parse_coding_task_document
    description: "Parse Coding Task Document to extract estimate_n and sub_phases"
    category: data
    allowed_roles: []  # Capability boundary managed by Actor.allowed_tools
    parameters:
      text:
        type: string
        required: true
        description: "Document text (Markdown or JSON)"
    python:
      module: "coding_task_document_parser"
      class: "CodingTaskDocumentParser"
      constructor_args: {}
      method: "parse"
      call_mode: direct
```

### Usage in Actors

**✅ Correct Usage (via Kitbag tool):**

```python
# In result_router.py or phase_dispatcher.py
class ResultRouter(Actor):
    allowed_tools = ["parse_coding_task_document"]  # Declare permission
    
    async def act(self, task: Task, context: ExecutionContext) -> ActorResponse:
        doc_text = self._get_upstream_document(context, task)
        
        # First turn: request tool call
        if context.metadata.get("tool_result") is None:
            return ActorResponse(
                type=ActorResponseType.TOOL_CALL,
                content=ToolCall(
                    name="parse_coding_task_document",
                    params={"text": doc_text},
                    caller_role=self.role
                )
            )
        
        # Second turn: process result
        tool_result = context.metadata["tool_result"]
        if tool_result.success:
            parse_result = tool_result.data  # dict from ParseResult
            estimate_n = parse_result["estimate_n"]
            # ... routing logic ...
```

**❌ Incorrect Usage (direct import - prohibited):**

```python
# ❌ DO NOT DO THIS
from coding_task_document_parser import CodingTaskDocumentParser

result = CodingTaskDocumentParser.parse(text)  # Violates architecture
```

**Enforcement:** The `RegistrationCoordinator` validates that no Actor code directly imports this library during system startup.

### Tool Result Structure

```python
ToolResult(
    success=True,
    data={
        "estimate_n": 15,
        "sub_phases": None,  # or list of dicts
        "raw_document": "...",
        "source_type": "architect",
        "parse_warnings": []
    },
    tool_name="parse_coding_task_document",
    error=None,
    elapsed_ms=12
)
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=coding_task_document_parser --cov-report=html

# Run specific test file
pytest tests/test_parser_architect.py -v
```

### Project Structure

```
coding_task_document_parser/
├── __init__.py              # Public API exports
├── models.py                # Data models (ParseResult, SubPhase)
├── parser.py                # Orchestrator (CodingTaskDocumentParser)
├── termination.py           # Termination line regex operations
├── source_detector.py       # Format detection
├── json_parser.py           # JSON parsing
├── history_collector.py     # History scanning
└── content_extractor.py     # Content extraction

tests/
├── conftest.py              # Shared fixtures
├── test_models.py
├── test_termination.py
├── test_source_detector.py
├── test_json_parser.py
├── test_history_collector.py
├── test_content_extractor.py
├── test_parser_architect.py
├── test_parser_engineer.py
└── test_parser_edge_cases.py
```

### Design Principles

1. **Zero External Dependencies** — Stdlib only (`re`, `json`, `dataclasses`)
2. **No Exception Propagation** — All errors → `parse_warnings`
3. **Static Method API** — All methods are `@staticmethod`
4. **Last-Match Semantics** — Use last termination line when multiple exist
5. **Type Safety** — Full type hints with Python 3.10+ syntax

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Add tests for new functionality
4. Ensure all tests pass (`pytest`)
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Support

- **Documentation:** [README.md](README.md)
- **Bug Reports:** [GitHub Issues](https://github.com/agent-os/coding-task-document-parser/issues)
- **Source Code:** [GitHub Repository](https://github.com/agent-os/coding-task-document-parser)

## Changelog

### v1.0.0 (2024-01-XX)

- Initial release
- Support for architect/engineer/JSON formats
- Zero external dependencies
- Comprehensive test coverage (75+ tests)
- Full type hints support
