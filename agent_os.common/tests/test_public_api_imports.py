"""公共 API 导入与基础可用性测试。"""

from __future__ import annotations

from agent_os.common import (
    Actor,
    DeterministicActor,
    InMemoryEventBus,
    LlmGatewayConfig,
    MemoryConfig,
    RuntimeConfig,
    StepProgress,
    TaskCreated,
    TaskStatus,
)


def test_top_level_event_imports_work() -> None:
    """应可直接从 agent_os.common 导入事件类型。"""
    created = TaskCreated(
        task_id="task-1",
        name="demo",
        role="coder",
        status=TaskStatus.PENDING,
    )
    progress = StepProgress(task_id="task-1", step_depth=1)
    assert created.task_id == "task-1"
    assert progress.step_depth == 1


def test_top_level_core_exports_work() -> None:
    """应可导入核心类型并完成基本实例化。"""
    bus = InMemoryEventBus()
    runtime_cfg = RuntimeConfig()
    memory_cfg = MemoryConfig()
    llm_cfg = LlmGatewayConfig(
        base_url="http://localhost:8000",
        token="token",
        project_id=1,
    )

    assert isinstance(bus, InMemoryEventBus)
    assert runtime_cfg.max_step_depth == 50
    assert memory_cfg.max_items_per_context == 20
    assert llm_cfg.project_id == 1


def test_actor_types_exposed_for_type_hinting() -> None:
    """Actor 与 DeterministicActor 必须可被导入使用。"""
    assert Actor.__name__ == "Actor"
    assert DeterministicActor.__name__ == "DeterministicActor"