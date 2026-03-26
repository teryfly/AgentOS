# Kitbag Architecture

This document provides detailed architectural documentation for the Kitbag module.

## Overview

Kitbag is the **Tool Execution Hub** for Agent OS, responsible for:
- Tool registration and management
- Multi-protocol tool execution
- Parameter validation and permission checking
- Result standardization

## Design Principles

1. **Declarative Registration**: All tools defined via YAML, zero code changes for new tools
2. **Protocol Abstraction**: Adapter pattern for Python/HTTP/Subprocess, extensible to gRPC/MCP
3. **Fail-Safe Execution**: All exceptions captured internally, callers only receive ToolResult
4. **Synchronous Interface**: `execute()` is synchronous; async contexts use `run_in_executor`
5. **Permission Fallback**: `allowed_roles` is safety net for high-risk tools; empty list = unrestricted
6. **Result Standardization**: All returns normalized to ToolResult with `tool_name` + `elapsed_ms`

## Execution Pipeline

The execution pipeline follows these steps:

1. **Lookup**: Verify tool exists in registry
2. **Permission Check**: Enforce `allowed_roles` for high-risk tools
3. **Parameter Validation**: Check required fields, types, enums, fill defaults
4. **Execute**: Call tool implementation
5. **Time Measurement**: Record elapsed time in milliseconds
6. **Standardize**: Normalize result to ToolResult
7. **Exception Handling**: Catch all errors and convert to ToolResult(success=False)

## Protocol Adapters

### Python Protocol
- Supports direct, generator, and async call modes
- Generator mode runs in ThreadPoolExecutor
- Dynamic import via importlib

### HTTP Protocol
- Built on httpx library
- Supports path parameters, query string, body mapping
- Bearer authentication via environment variables

### Subprocess Protocol
- Executes shell commands via subprocess.run
- Captures stdout/stderr
- Timeout and working directory support

## Extension Points

New protocols can be added by:
1. Implementing `ProtocolAdapter` abstract class
2. Creating corresponding Tool subclass
3. Registering adapter in `YamlToolLoader.PROTOCOL_ADAPTERS`

No changes needed to core Kitbag code.
