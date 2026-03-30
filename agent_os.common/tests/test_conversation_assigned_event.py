"""ConversationAssigned 事件测试。"""

from __future__ import annotations

import asyncio
from typing import List

import agent_os.common
from agent_os.common import (
    ConversationAssigned,
    InMemoryEventBus,
)


def test_conversation_assigned_can_be_imported() -> None:
    """ConversationAssigned 应可从 agent_os.common 导入。"""
    assert hasattr(agent_os.common, "ConversationAssigned")


def test_conversation_assigned_in_all_export_list() -> None:
    """ConversationAssigned 应存在于 __all__ 导出列表。"""
    assert "ConversationAssigned" in agent_os.common.__all__


def test_conversation_assigned_can_be_instantiated() -> None:
    """ConversationAssigned 应可正常实例化。"""
    event = ConversationAssigned(task_id="task-001", conv_id="conv-abc123")
    assert event.task_id == "task-001"
    assert event.conv_id == "conv-abc123"


def test_conversation_assigned_event_bus_subscription_works() -> None:
    """EventBus 应可订阅并分发 ConversationAssigned 事件。"""
    bus = InMemoryEventBus()
    received: List[ConversationAssigned] = []

    async def handler(event: ConversationAssigned) -> None:
        received.append(event)

    bus.subscribe(ConversationAssigned, handler)

    async def run() -> None:
        await bus.publish(
            ConversationAssigned(task_id="task-002", conv_id="conv-xyz789")
        )

    asyncio.run(run())

    assert len(received) == 1
    assert received[0].task_id == "task-002"
    assert received[0].conv_id == "conv-xyz789"


def test_conversation_assigned_multiple_handlers_all_called() -> None:
    """多个订阅者应均收到 ConversationAssigned 事件。"""
    bus = InMemoryEventBus()
    calls: List[str] = []

    async def handler_a(event: ConversationAssigned) -> None:
        calls.append(f"a:{event.task_id}")

    async def handler_b(event: ConversationAssigned) -> None:
        calls.append(f"b:{event.conv_id}")

    bus.subscribe(ConversationAssigned, handler_a)
    bus.subscribe(ConversationAssigned, handler_b)

    async def run() -> None:
        await bus.publish(
            ConversationAssigned(task_id="task-003", conv_id="conv-multi")
        )

    asyncio.run(run())

    assert calls == ["a:task-003", "b:conv-multi"]


def test_conversation_assigned_handler_exception_isolated() -> None:
    """单个 ConversationAssigned 处理器异常不应阻断后续处理器。"""
    bus = InMemoryEventBus()
    calls: List[str] = []

    async def handler_fail(event: ConversationAssigned) -> None:
        calls.append("fail")
        raise RuntimeError("expected failure")

    async def handler_ok(event: ConversationAssigned) -> None:
        calls.append("ok")

    bus.subscribe(ConversationAssigned, handler_fail)
    bus.subscribe(ConversationAssigned, handler_ok)

    async def run() -> None:
        await bus.publish(
            ConversationAssigned(task_id="task-004", conv_id="conv-error")
        )

    asyncio.run(run())

    assert calls == ["fail", "ok"]