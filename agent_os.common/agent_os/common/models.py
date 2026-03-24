"""
agent_os/common/models.py
Agent OS 所有共享数据模型。仅依赖 Python 标准库。
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .enums import ActorResponseType, MemorySource, MemoryType, TaskStatus, ToolCategory


# ---------------------------------------------------------------------------
# 任务相关
# ---------------------------------------------------------------------------


@dataclass
class TaskResult:
    """任务执行结果。"""

    success: bool
    data: Any
    error: Optional[str] = None


@dataclass
class Task:
    """任务实体。"""

    id: str
    name: str
    description: str
    role: str
    status: TaskStatus
    depends_on: List[str] = field(default_factory=list)
    children: List[str] = field(default_factory=list)
    result: Optional[TaskResult] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: int = 0
    updated_at: int = 0
    version: int = 0


@dataclass
class TaskRuntimeState:
    """任务运行时状态。"""

    task_id: str
    runtime_data: Dict[str, Any] = field(default_factory=dict)
    version: int = 0
    updated_at: int = 0


@dataclass
class TaskBatchItem:
    """批量创建任务的单条输入项。"""

    ref_id: str
    name: str
    description: str
    role: str
    depends_on_refs: List[str] = field(default_factory=list)
    depends_on_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionContext:
    """Actor 执行上下文。"""

    task_id: str
    step_depth: int
    max_step_depth: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    injected_actors: Optional[Dict[str, Any]] = None


@dataclass
class ActorResponse:
    """Actor 执行响应。"""

    type: ActorResponseType
    content: Any


# ---------------------------------------------------------------------------
# Actor 基类
# ---------------------------------------------------------------------------


class Actor:
    """
    所有 Actor 的基类。

    子类应定义:
      - name / role / description / skills / allowed_tools
      - act(task, context) 异步方法
    """

    name: str
    role: str
    description: str
    skills: List[str]
    allowed_tools: List[str]

    async def act(self, task: "Task", context: "ExecutionContext") -> "ActorResponse":
        """执行一步推理。子类必须覆盖。"""
        raise NotImplementedError(
            f"{type(self).__name__}.act() is not implemented. "
            "Subclasses must override this method."
        )


class DeterministicActor(Actor):
    """
    不调用 LLM 的确定性逻辑 Actor 基类。
    通过代码注册，通常用于路由、分发、聚合、格式转换等纯逻辑场景。
    """

    allowed_tools: List[str] = []


# ---------------------------------------------------------------------------
# 工具相关
# ---------------------------------------------------------------------------


@dataclass
class ParameterDef:
    """工具参数定义。"""

    type: str
    required: bool
    description: str
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None


@dataclass
class ToolSchema:
    """工具 schema。"""

    name: str
    description: str
    category: ToolCategory
    parameters: Dict[str, ParameterDef] = field(default_factory=dict)


@dataclass
class ToolCall:
    """Actor 发起的工具调用请求。"""

    name: str
    params: Dict[str, Any]
    caller_role: Optional[str] = None


@dataclass
class ToolResult:
    """工具执行结果。"""

    success: bool
    data: Any
    tool_name: str
    error: Optional[str] = None
    elapsed_ms: int = 0


# ---------------------------------------------------------------------------
# 记忆相关
# ---------------------------------------------------------------------------


@dataclass
class MemoryItem:
    """单条记忆项。"""

    task_id: str
    type: MemoryType
    source: MemorySource
    content: Any
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: int = 0


@dataclass
class MemoryContext:
    """任务记忆上下文。"""

    task_id: str
    items: List[MemoryItem]
    truncated: bool = False


# ---------------------------------------------------------------------------
# 规划相关
# ---------------------------------------------------------------------------


@dataclass
class PlannedTask:
    """规划阶段的任务结构。"""

    ref_id: str
    name: str
    description: str
    role: str
    depends_on_refs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Plan:
    """任务规划结果。"""

    steps: List[PlannedTask]


@dataclass
class RouterRule:
    """角色路由规则。"""

    condition: str
    preferred_roles: List[str]
    avoid_roles: List[str]
    reason: str


@dataclass
class RoleRouterConfig:
    """角色路由配置。"""

    rules: List[RouterRule]
    fallback_role: str
    forbidden: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# LLM 相关
# ---------------------------------------------------------------------------


@dataclass
class LlmConfig:
    """LLM 推理配置。"""

    model: str
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout_ms: int = 60000
    use_stream: bool = False


# ---------------------------------------------------------------------------
# 协作相关
# ---------------------------------------------------------------------------


@dataclass
class GroupTurn:
    """多 Actor 协作中的单轮输出。"""

    round: int
    actor_role: str
    response_type: ActorResponseType
    content: Any


def _make_serializable(value: Any) -> Any:
    """递归将对象转换为 JSON 可序列化结构。"""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(k): _make_serializable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_make_serializable(v) for v in value]
    if hasattr(value, "__dataclass_fields__"):
        return {k: _make_serializable(getattr(value, k)) for k in value.__dataclass_fields__}
    if hasattr(value, "value"):  # Enum 兼容
        return getattr(value, "value")
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)


@dataclass
class GroupState:
    """协作状态，可持久化到 TaskRuntimeState。"""

    history: List[GroupTurn] = field(default_factory=list)
    shared_context: Dict[str, Any] = field(default_factory=dict)
    current_round: int = 0
    finished: bool = False
    waiting_for_member: Optional[str] = None
    waiting_input_prompt: Optional[str] = None
    resume_round_index: Optional[int] = None
    pending_input: Optional[str] = None
    accumulated_steps: str = ""

    def to_dict(self) -> dict:
        """序列化为可 JSON 存储的 dict。"""
        return {
            "history": [
                {
                    "round": turn.round,
                    "actor_role": turn.actor_role,
                    "response_type": turn.response_type.value,
                    "content": _make_serializable(turn.content),
                }
                for turn in self.history
            ],
            "shared_context": _make_serializable(self.shared_context),
            "current_round": self.current_round,
            "finished": self.finished,
            "waiting_for_member": self.waiting_for_member,
            "waiting_input_prompt": self.waiting_input_prompt,
            "resume_round_index": self.resume_round_index,
            "pending_input": self.pending_input,
            "accumulated_steps": self.accumulated_steps,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GroupState":
        """从 dict 反序列化 GroupState。"""
        history_items: List[GroupTurn] = []
        for raw in data.get("history", []):
            response_type = raw.get("response_type", ActorResponseType.CONTINUE.value)
            history_items.append(
                GroupTurn(
                    round=int(raw.get("round", 0)),
                    actor_role=str(raw.get("actor_role", "")),
                    response_type=ActorResponseType(response_type),
                    content=raw.get("content"),
                )
            )

        return cls(
            history=history_items,
            shared_context=data.get("shared_context", {}),
            current_round=int(data.get("current_round", 0)),
            finished=bool(data.get("finished", False)),
            waiting_for_member=data.get("waiting_for_member"),
            waiting_input_prompt=data.get("waiting_input_prompt"),
            resume_round_index=data.get("resume_round_index"),
            pending_input=data.get("pending_input"),
            accumulated_steps=str(data.get("accumulated_steps", "")),
        )


# ---------------------------------------------------------------------------
# 能力描述相关
# ---------------------------------------------------------------------------


@dataclass
class ToolCapabilitySummary:
    """工具能力摘要。"""

    name: str
    description: str
    category: str


@dataclass
class ActorMeta:
    """Actor 元信息。"""

    name: str
    role: str
    description: str
    skills: List[str]
    actor_type: str
    allowed_tools: List[str]
    tool_capabilities: List[ToolCapabilitySummary] = field(default_factory=list)