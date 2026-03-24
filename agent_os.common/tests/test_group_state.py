"""GroupState 序列化/反序列化测试。"""

from __future__ import annotations

import json

from agent_os.common import ActorResponseType, GroupState, GroupTurn


def test_group_state_to_dict_is_json_serializable() -> None:
    """to_dict 输出应可直接被 json.dumps 序列化。"""
    state = GroupState(
        history=[
            GroupTurn(
                round=1,
                actor_role="planner",
                response_type=ActorResponseType.CONTINUE,
                content={"message": "go", "tags": ["a", "b"]},
            )
        ],
        shared_context={"current_step_label": "Step [1/3]"},
        current_round=1,
    )
    data = state.to_dict()
    encoded = json.dumps(data, ensure_ascii=False)
    assert "Step [1/3]" in encoded
    assert data["history"][0]["response_type"] == ActorResponseType.CONTINUE.value


def test_group_state_round_trip_restores_enum_and_fields() -> None:
    """from_dict 应正确恢复核心字段与响应类型枚举。"""
    original = GroupState(
        history=[
            GroupTurn(
                round=2,
                actor_role="reviewer",
                response_type=ActorResponseType.FINAL,
                content="done",
            )
        ],
        shared_context={"k": "v"},
        current_round=2,
        finished=True,
        accumulated_steps="S1\nS2",
    )

    restored = GroupState.from_dict(original.to_dict())

    assert restored.current_round == 2
    assert restored.finished is True
    assert restored.history[0].response_type == ActorResponseType.FINAL
    assert restored.history[0].actor_role == "reviewer"
    assert restored.shared_context["k"] == "v"
    assert restored.accumulated_steps == "S1\nS2"