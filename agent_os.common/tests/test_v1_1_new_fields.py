"""v1.1.0 新增字段完整性测试。"""

from __future__ import annotations

from agent_os.common import (
    ActorMeta,
    ActorResponseType,
    GroupState,
    GroupTurn,
    ModelPoolEntry,
    StepProgress,
    TaskStatus,
    TaskWaitingInput,
)


def test_group_state_code_block_recovery_count_defaults_to_zero() -> None:
    """GroupState.code_block_recovery_count 默认值为 0。"""
    state = GroupState()
    assert state.code_block_recovery_count == 0


def test_group_state_code_block_recovery_count_can_be_set() -> None:
    """GroupState.code_block_recovery_count 可显式设置。"""
    state = GroupState(code_block_recovery_count=5)
    assert state.code_block_recovery_count == 5


def test_group_state_serialization_includes_code_block_recovery_count() -> None:
    """GroupState.to_dict() 应包含 code_block_recovery_count。"""
    state = GroupState(code_block_recovery_count=3)
    data = state.to_dict()
    assert "code_block_recovery_count" in data
    assert data["code_block_recovery_count"] == 3


def test_group_state_deserialization_restores_code_block_recovery_count() -> None:
    """GroupState.from_dict() 应正确恢复 code_block_recovery_count。"""
    data = {
        "history": [],
        "shared_context": {},
        "current_round": 0,
        "finished": False,
        "accumulated_steps": "",
        "code_block_recovery_count": 7,
    }
    state = GroupState.from_dict(data)
    assert state.code_block_recovery_count == 7


def test_group_state_deserialization_handles_missing_code_block_recovery_count() -> None:
    """GroupState.from_dict() 对缺失 code_block_recovery_count 应默认为 0（向后兼容）。"""
    data = {
        "history": [],
        "shared_context": {},
        "current_round": 1,
        "finished": False,
        "accumulated_steps": "S1",
    }
    state = GroupState.from_dict(data)
    assert state.code_block_recovery_count == 0


def test_group_state_round_trip_preserves_code_block_recovery_count() -> None:
    """GroupState 完整往返序列化应保留 code_block_recovery_count。"""
    original = GroupState(
        history=[
            GroupTurn(
                round=1,
                actor_role="coder",
                response_type=ActorResponseType.CONTINUE,
                content="test",
            )
        ],
        code_block_recovery_count=4,
    )
    restored = GroupState.from_dict(original.to_dict())
    assert restored.code_block_recovery_count == 4


def test_task_waiting_input_reason_defaults_to_none() -> None:
    """TaskWaitingInput.reason 默认值为 None。"""
    event = TaskWaitingInput(task_id="t1")
    assert event.reason is None


def test_task_waiting_input_prompt_defaults_to_none() -> None:
    """TaskWaitingInput.prompt 默认值为 None。"""
    event = TaskWaitingInput(task_id="t1")
    assert event.prompt is None


def test_task_waiting_input_can_set_reason_only() -> None:
    """TaskWaitingInput 可仅设置 reason。"""
    event = TaskWaitingInput(
        task_id="t1",
        reason="code_block_recovery_exhausted",
    )
    assert event.reason == "code_block_recovery_exhausted"
    assert event.prompt is None


def test_task_waiting_input_can_set_prompt_only() -> None:
    """TaskWaitingInput 可仅设置 prompt。"""
    event = TaskWaitingInput(
        task_id="t1",
        prompt="请输入文件数量",
    )
    assert event.reason is None
    assert event.prompt == "请输入文件数量"


def test_task_waiting_input_can_set_both_reason_and_prompt() -> None:
    """TaskWaitingInput 可同时设置 reason 和 prompt。"""
    event = TaskWaitingInput(
        task_id="t1",
        reason="code_block_recovery_exhausted",
        prompt="代码块恢复次数已超限，请检查输出格式",
    )
    assert event.reason == "code_block_recovery_exhausted"
    assert event.prompt == "代码块恢复次数已超限，请检查输出格式"


def test_step_progress_is_last_message_complete_defaults_to_true() -> None:
    """StepProgress.is_last_message_complete 默认值为 True。"""
    event = StepProgress(task_id="t1", step_depth=1)
    assert event.is_last_message_complete is True


def test_step_progress_can_set_is_last_message_complete_false() -> None:
    """StepProgress.is_last_message_complete 可显式设置为 False。"""
    event = StepProgress(
        task_id="t1",
        step_depth=2,
        is_last_message_complete=False,
    )
    assert event.is_last_message_complete is False


def test_step_progress_all_fields_work_together() -> None:
    """StepProgress 所有字段可协同工作。"""
    event = StepProgress(
        task_id="t1",
        step_depth=3,
        step_label="Step [3/10]",
        last_message="Processing...",
        is_last_message_complete=True,
    )
    assert event.task_id == "t1"
    assert event.step_depth == 3
    assert event.step_label == "Step [3/10]"
    assert event.last_message == "Processing..."
    assert event.is_last_message_complete is True


def test_model_pool_entry_required_fields_only() -> None:
    """ModelPoolEntry 最小构造（仅必需字段）。"""
    entry = ModelPoolEntry(
        alias="frontend",
        model="claude-sonnet-4-6",
        description="前端开发任务",
    )
    assert entry.alias == "frontend"
    assert entry.model == "claude-sonnet-4-6"
    assert entry.description == "前端开发任务"
    assert entry.temperature is None
    assert entry.max_tokens is None


def test_model_pool_entry_with_optional_fields() -> None:
    """ModelPoolEntry 可设置可选字段。"""
    entry = ModelPoolEntry(
        alias="bugfix",
        model="claude-sonnet-4-6",
        description="调试修复",
        temperature=0.3,
        max_tokens=2048,
    )
    assert entry.temperature == 0.3
    assert entry.max_tokens == 2048


def test_actor_meta_model_pool_defaults_to_empty_list() -> None:
    """ActorMeta.model_pool 默认为空列表。"""
    meta = ActorMeta(
        name="Test",
        role="test",
        description="test actor",
        skills=[],
        actor_type="llm",
        allowed_tools=[],
    )
    assert meta.model_pool == []


def test_actor_meta_model_pool_can_be_set() -> None:
    """ActorMeta.model_pool 可设置模型候选列表。"""
    entry1 = ModelPoolEntry(
        alias="default",
        model="claude-sonnet-4-6",
        description="通用任务",
    )
    entry2 = ModelPoolEntry(
        alias="fast",
        model="gpt-4o-mini",
        description="快速响应",
        temperature=0.5,
    )

    meta = ActorMeta(
        name="Engineer",
        role="engineer",
        description="编码工程师",
        skills=["coding"],
        actor_type="llm",
        allowed_tools=["read_file", "write_file"],
        model_pool=[entry1, entry2],
    )

    assert len(meta.model_pool) == 2
    assert meta.model_pool[0].alias == "default"
    assert meta.model_pool[1].alias == "fast"
    assert meta.model_pool[1].temperature == 0.5


def test_actor_meta_model_pool_preserves_entry_order() -> None:
    """ActorMeta.model_pool 应保留条目顺序。"""
    entries = [
        ModelPoolEntry(alias=f"model{i}", model=f"m{i}", description=f"d{i}")
        for i in range(5)
    ]

    meta = ActorMeta(
        name="Test",
        role="test",
        description="test",
        skills=[],
        actor_type="llm",
        allowed_tools=[],
        model_pool=entries,
    )

    for i, entry in enumerate(meta.model_pool):
        assert entry.alias == f"model{i}"