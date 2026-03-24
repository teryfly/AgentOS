"""核心模型实例化行为测试。"""

from __future__ import annotations

import uuid

from agent_os.common import (
    MemoryItem,
    MemorySource,
    MemoryType,
    Task,
    TaskStatus,
    ToolResult,
)


def test_tool_result_can_be_instantiated_with_required_fields_only() -> None:
    """ToolResult 必须支持最小入参构造。"""
    result = ToolResult(success=True, data={}, tool_name="test_tool")
    assert result.success is True
    assert result.data == {}
    assert result.tool_name == "test_tool"
    assert result.error is None


def test_memory_item_auto_generates_uuid4_id() -> None:
    """MemoryItem 不传 id 时应自动生成合法 UUID4。"""
    item = MemoryItem(
        task_id="task-001",
        type=MemoryType.SHORT,
        source=MemorySource.TOOL,
        content={"k": "v"},
    )
    parsed = uuid.UUID(item.id)
    assert parsed.version == 4
    assert item.task_id == "task-001"


def test_task_mutable_defaults_are_isolated_between_instances() -> None:
    """dataclass 可变默认值必须隔离，不应跨实例共享。"""
    t1 = Task(
        id="t1",
        name="task1",
        description="d1",
        role="coder",
        status=TaskStatus.PENDING,
    )
    t2 = Task(
        id="t2",
        name="task2",
        description="d2",
        role="coder",
        status=TaskStatus.PENDING,
    )

    t1.depends_on.append("x")
    t1.metadata["a"] = 1

    assert t2.depends_on == []
    assert t2.metadata == {}