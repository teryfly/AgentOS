"""
agent_os/common/models.py
Agent OS 所有共享数据模型。无外部依赖，仅使用标准库。
"""
from __future__ import annotations
import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from .enums import (
    ActorResponseType,
    CollaborationStrategy,  # noqa: F401
    MemorySource,
    MemoryType,
    TaskStatus,
    ToolCategory,
)
# ---------------------------------------------------------------------------
# 任务相关
# ---------------------------------------------------------------------------
@dataclass
class TaskResult:
    success: bool
    data: Any
    error: Optional[str] = None
@dataclass
class Task:
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
    task_id: str
    runtime_data: Dict[str, Any] = field(default_factory=dict)
    version: int = 0
    updated_at: int = 0
@dataclass
class TaskBatchItem:
    ref_id: str
    name: str
    description: str
    role: str
    depends_on_refs: List[str] = field(default_factory=list)
    depends_on_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
@dataclass
class ExecutionContext:
    task_id: str
    step_depth: int
    max_step_depth: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    injected_actors: Optional[Dict[str, Any]] = None
@dataclass
class ActorResponse:
    type: ActorResponseType
    content: Any
# ---------------------------------------------------------------------------
# Actor 基类层级
# 继承关系：Actor → DeterministicActor
#                  → LlmActor          （v1.1 新增）
#                  → GroupActor        （v1.1 新增）
# ---------------------------------------------------------------------------
class Actor:
    """
    所有 Actor 的根基类，定义公共接口契约。
    子类通过 Builder（YamlActorLoader / 代码注册）设置实例属性，
    因此基类使用类型注解声明接口，不设定实例默认值。
    子类必须实现的内容：
        1. 在 __init__（或 Builder 注入）时设置 name / role / description /
           skills / allowed_tools 等实例属性。
        2. 覆盖 act() 异步方法。
    AgentRuntime 调用方式：
        response = await actor.act(task, context)
    """
    # 公共属性声明（供静态类型检查工具识别）
    name: str
    role: str
    description: str
    skills: List[str]
    allowed_tools: List[str]
    async def act(
        self,
        task: "Task",
        context: "ExecutionContext",
    ) -> "ActorResponse":
        """
        执行 Actor 的推理单步（异步）。
        由 AgentRuntime 的 step_loop 以 await actor.act(task, context) 调用。
        所有子类必须覆盖此方法，否则 AgentRuntime 将捕获 NotImplementedError 并 fail_task。
        """
        raise NotImplementedError(
            f"{type(self).__name__}.act() is not implemented. "
            "Subclasses must override this method."
        )
class DeterministicActor(Actor):
    """
    不调用 LLM 的确定性逻辑 Actor 基类，通过代码注册使用。
    无额外字段，仅作类型标记，供 ActorRegistry 区分注册来源与调用路径。
    使用场景：
      - 路由判断（result_router：解析文件数 N，路由到不同执行组）
      - 子阶段分发（phase_dispatcher：解析 engineer 的 sub_phases，创建串行任务链）
      - 格式转换（将一种 ActorResponse 内容格式转化为另一种）
      - 纯逻辑聚合（无需 LLM 推理的任务编排节点）
    设计约束：
      - 必须实现 act() 方法，遵循 ActorResponse 协议
      - 同样需要遵循 description 三要素规范
      - 通过 registry.register() 代码注册，不通过 YAML 文件
      - 代码注册必须在 YamlActorLoader.load_from_dir() 之后、
        RegistrationCoordinator.validate() 之前完成
      - 配置参数（如 file_limit）在注册时通过代码直接赋值，不通过 YAML 注入
    """
    # 公共属性声明（供静态类型检查工具识别）
    name: str
    role: str
    description: str
    skills: List[str]
    allowed_tools: List[str] = []    # 通常为空，DeterministicActor 一般不直接调用工具
class LlmActor(Actor):
    """
    调用 LLM 的 Actor 基类，通过 YamlActorLoader 加载 YAML 定义并注入属性。   # v1.1 新增
    字段说明：
      - system_prompt：Actor 系统提示词，来自 YAML 的 system_prompt 字段。
      - llm_config：LLM 调用参数（模型、温度等），来自 YAML 的 llm_config 节。
      - _llm_gateway：运行时由 AgentRuntime 注入的 LlmGateway 实例；
                      类型标注为 Any 以避免与 agent_os.llm_gateway 包产生循环导入，
                      实际类型为 agent_os.llm_gateway.LlmGateway。
    调用方不应直接读写 _llm_gateway；AgentRuntime 在任务启动前完成注入。
    """
    # 公共属性声明（供静态类型检查工具识别）
    name: str
    role: str
    description: str
    skills: List[str]
    allowed_tools: List[str]
    # LlmActor 特定属性
    system_prompt: str
    llm_config: LlmConfig           # 使用 from __future__ import annotations 延迟求值
    _llm_gateway: Any               # 运行时注入，不通过 YAML；实际类型为 LlmGateway
class GroupActor(Actor):
    """
    协作组 Actor 基类，协调多个子 Actor 按指定策略共同完成复杂任务。   # v1.1 新增
    字段说明：
      - members：参与协作的成员 Actor 的 role 名称列表，由 YamlActorLoader 注入。
      - strategy：协作调度策略，对应 CollaborationStrategy 枚举值。
      - max_rounds：最大协作轮次上限；超出后 AgentRuntime 将任务置为 FAILED。
      - max_code_block_recovery：单批次最大代码块恢复次数阈值；
                                  GroupState.code_block_recovery_count 超出此值后，
                                  以 reason="code_block_recovery_exhausted" 发布
                                  TaskWaitingInput 事件并暂停任务。
    GroupState 在运行时由 AgentRuntime 通过 TaskCenter 持久化，不作为类属性存储。
    """
    # 公共属性声明（供静态类型检查工具识别）
    name: str
    role: str
    description: str
    skills: List[str]
    allowed_tools: List[str]
    # GroupActor 特定属性
    members: List[str]                  # 成员 Actor 的 role 名称列表
    strategy: CollaborationStrategy     # 协作调度策略
    max_rounds: int                     # 最大协作轮次
    max_code_block_recovery: int        # 单批次代码块恢复次数上限
# ---------------------------------------------------------------------------
# 工具相关
# ---------------------------------------------------------------------------
@dataclass
class ParameterDef:
    type: str
    required: bool
    description: str
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None
@dataclass
class ToolSchema:
    name: str
    description: str
    category: ToolCategory
    parameters: Dict[str, ParameterDef] = field(default_factory=dict)
@dataclass
class ToolCall:
    name: str
    params: Dict[str, Any]
    caller_role: Optional[str] = None
@dataclass
class ToolResult:
    # ⚠️ 无默认值字段必须置于有默认值字段之前
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
    task_id: str
    type: MemoryType
    source: MemorySource
    content: Any
    # id 由系统自动生成，调用时无需传递
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: int = 0
@dataclass
class MemoryContext:
    task_id: str
    items: List[MemoryItem]
    truncated: bool = False
# ---------------------------------------------------------------------------
# 规划相关
# ---------------------------------------------------------------------------
@dataclass
class PlannedTask:
    ref_id: str
    name: str
    description: str
    role: str
    depends_on_refs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
@dataclass
class Plan:
    steps: List[PlannedTask]
@dataclass
class RouterRule:
    condition: str
    preferred_roles: List[str]
    avoid_roles: List[str]
    reason: str
@dataclass
class RoleRouterConfig:
    rules: List[RouterRule]
    fallback_role: str
    forbidden: List[str] = field(default_factory=list)
# ---------------------------------------------------------------------------
# LLM 相关
# ---------------------------------------------------------------------------
@dataclass
class LlmConfig:
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
    round: int
    actor_role: str
    response_type: ActorResponseType
    content: Any
def _make_serializable(value: Any) -> Any:
    """将任意值递归转换为 JSON 可序列化的原生类型。"""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {k: _make_serializable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_make_serializable(item) for item in value]
    if hasattr(value, "__dataclass_fields__"):
        return {k: _make_serializable(getattr(value, k))
                for k in value.__dataclass_fields__}
    if hasattr(value, "value"):
        return value.value
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)
@dataclass
class GroupState:
    history: List[GroupTurn] = field(default_factory=list)
    shared_context: Dict[str, Any] = field(default_factory=dict)
    current_round: int = 0
    finished: bool = False
    waiting_for_member: Optional[str] = None
    waiting_input_prompt: Optional[str] = None
    resume_round_index: Optional[int] = None
    pending_input: Optional[str] = None
    accumulated_steps: str = ""
    code_block_recovery_count: int = 0  # v1.1 新增：当前步骤批次代码块恢复次数，用于熔断防死循环
    # 注意：_rerun_current_actor 是运行时临时标志，不参与序列化/持久化
    def to_dict(self) -> dict:
        """序列化为 JSON 可存储的 dict（供 TaskCenter 持久化）。"""
        return {
            "history": [
                {
                    "round": t.round,
                    "actor_role": t.actor_role,
                    "response_type": t.response_type,
                    "content": _make_serializable(t.content),
                }
                for t in self.history
            ],
            "shared_context": _make_serializable(self.shared_context),
            "current_round": self.current_round,
            "finished": self.finished,
            "waiting_for_member": self.waiting_for_member,
            "waiting_input_prompt": self.waiting_input_prompt,
            "resume_round_index": self.resume_round_index,
            "pending_input": self.pending_input,
            "accumulated_steps": self.accumulated_steps,
            "code_block_recovery_count": self.code_block_recovery_count,  # v1.1 新增
        }
    @classmethod
    def from_dict(cls, data: dict) -> "GroupState":
        """从持久化 dict 还原 GroupState（resume 场景使用）。"""
        history = [
            GroupTurn(
                round=t["round"],
                actor_role=t["actor_role"],
                response_type=ActorResponseType(t["response_type"]),
                content=t["content"],
            )
            for t in data.get("history", [])
        ]
        return cls(
            history=history,
            shared_context=data.get("shared_context", {}),
            current_round=data.get("current_round", 0),
            finished=data.get("finished", False),
            waiting_for_member=data.get("waiting_for_member"),
            waiting_input_prompt=data.get("waiting_input_prompt"),
            resume_round_index=data.get("resume_round_index"),
            pending_input=data.get("pending_input"),
            accumulated_steps=data.get("accumulated_steps", ""),
            # v1.1 新增：旧数据中若无此键，默认为 0，不抛出异常
            code_block_recovery_count=data.get("code_block_recovery_count", 0),
        )
# ---------------------------------------------------------------------------
# 能力描述相关
# ---------------------------------------------------------------------------
@dataclass
class ToolCapabilitySummary:
    name: str
    description: str
    category: str
@dataclass
class ModelPoolEntry:                        # v1.1 新增：多模型候选条目
    """
    Actor 支持的单个模型候选，供 CIO-agent 根据任务特征（前端/后端/调试等）选择目标模型。
    通过 ActorMeta.model_pool 聚合后对外暴露。
    """
    alias: str                              # 模型别名，如 "frontend"、"bugfix"
    model: str                              # 模型名称，如 "claude-sonnet-4-6"
    description: str                        # 适用场景描述，供 CIO-agent 选择依据
    temperature: Optional[float] = None    # 覆盖默认温度；None 表示沿用 Actor YAML 默认值
    max_tokens: Optional[int] = None       # 覆盖默认 max_tokens；None 表示沿用默认值
@dataclass
class ActorMeta:
    name: str
    role: str
    description: str
    skills: List[str]
    actor_type: str
    allowed_tools: List[str]
    tool_capabilities: List[ToolCapabilitySummary] = field(default_factory=list)
    model_pool: List[ModelPoolEntry] = field(default_factory=list)  # v1.1 新增
    # model_pool 供 CIO-agent 查询该 Actor 支持的模型候选列表，
    # 以便根据任务特征（前端/后端/调试）设置 preferred_model。
    # 未配置时为空列表，表示该 Actor 不暴露多模型选择能力。