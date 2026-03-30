"""
agent_os/common/events.py

领域事件与进度事件。
- TaskCenter 领域事件：描述任务生命周期状态变化，由 TaskCenter 发布。
- StepProgress 事件：描述推理步骤进度，由 AgentRuntime 发布。
- ConversationAssigned 事件：描述 LlmGateway 为任务绑定外部会话，由 LlmGateway 发布。

所有消费者（AgentRuntime、AgentStatusService、IntegrationLayer 等）均从此模块导入事件类型，
避免跨模块的循环依赖。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .enums import TaskStatus


# ---------------------------------------------------------------------------
# TaskCenter 领域事件（Task 生命周期）
# ---------------------------------------------------------------------------

@dataclass
class TaskCreated:
    """任务被创建时发布（初始状态 PENDING 或 WAITING_DEPENDENCY）。"""
    task_id: str
    name: str
    role: str
    status: TaskStatus


@dataclass
class TaskStarted:
    """任务状态变为 RUNNING 时发布。"""
    task_id: str


@dataclass
class TaskCompleted:
    """任务成功完成时发布。"""
    task_id: str
    result: Any  # TaskResult；使用 Any 避免循环导入


@dataclass
class TaskFailed:
    """任务失败时发布。"""
    task_id: str
    error: str


@dataclass
class TaskWaitingInput:
    """任务进入 WAITING_INPUT 状态时发布。"""
    task_id: str
    reason: Optional[str] = None  # v1.1 新增
    prompt: Optional[str] = None  # v1.1 新增  ← 修订
    # reason 常量约定（写在注释中）：
    # - None / 未设置：正常等待用户输入
    # - "code_block_recovery_exhausted"：代码块恢复次数超出 max_code_block_recovery
    # - 未来可扩展其他系统级错误原因
    #
    # prompt：由 AgentRuntime 从 response.content 提取后写入，
    # AgentStatusService 将其映射到 TaskSnapshot.waiting_prompt，
    # 用于向用户展示提示信息；None 表示无需展示额外提示。


@dataclass
class TaskWaitingDependency:
    """任务进入 WAITING_DEPENDENCY 状态时发布。"""
    task_id: str


@dataclass
class TaskUnblocked:
    """依赖满足、任务从 WAITING_DEPENDENCY 恢复为 PENDING 时发布。"""
    task_id: str


@dataclass
class TaskResumed:
    """用户提供输入、任务从 WAITING_INPUT 恢复为 RUNNING 时发布。"""
    task_id: str
    input_data: Any = None  # 由 AgentStatusService 用于可观测性，不持久化


# ---------------------------------------------------------------------------
# AgentRuntime 进度事件（可观测性）
# ---------------------------------------------------------------------------

@dataclass
class StepProgress:
    """
    推理步骤进度事件，由 AgentRuntime 在每轮 step_loop 后发布。
    AgentStatusService 订阅此事件以维护任务状态快照并向外部推送进度。
    """
    task_id: str
    step_depth: int
    step_label: Optional[str] = None    # 如 "Step [3/10]"，从 GroupActor 共享上下文提取
    last_message: Optional[str] = None  # 步骤输出摘要（前 200 字符）
    is_last_message_complete: bool = True  # v1.1 新增：当前 step 输出中三反引号（```）数量是否为偶数（即成对闭合）
    # is_last_message_complete 由 AgentRuntime._publish_step_progress 填充，
    # 供 IntegrationLayer 消费；GroupActor 内部独立处理恢复逻辑，两者互不依赖。


# ---------------------------------------------------------------------------
# LlmGateway 事件                                                   # v1.1 新增
# ---------------------------------------------------------------------------

@dataclass
class ConversationAssigned:
    """
    LlmGateway 为 task_id 分配（创建或首次绑定）外部 chat_backend 会话时发布。
    IntegrationLayer 订阅此事件，将 conv_id 写入 TaskSnapshot，
    供外部 CIO-agent 在需要回滚会话时查询。
    """
    task_id: str
    conv_id: str