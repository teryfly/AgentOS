"""
agent_os/common/events.py

领域事件与进度事件：
- TaskCenter 生命周期事件
- AgentRuntime 步骤进度事件

所有模块应统一从本模块导入事件类型，避免循环依赖。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .enums import TaskStatus


# ---------------------------------------------------------------------------
# TaskCenter 领域事件（任务生命周期）
# ---------------------------------------------------------------------------


@dataclass
class TaskCreated:
    """任务被创建（初始为 PENDING 或 WAITING_DEPENDENCY）。"""

    task_id: str
    name: str
    role: str
    status: TaskStatus


@dataclass
class TaskStarted:
    """任务进入 RUNNING。"""

    task_id: str


@dataclass
class TaskCompleted:
    """任务成功完成。"""

    task_id: str
    result: Any


@dataclass
class TaskFailed:
    """任务失败。"""

    task_id: str
    error: str


@dataclass
class TaskWaitingInput:
    """任务进入 WAITING_INPUT。"""

    task_id: str


@dataclass
class TaskWaitingDependency:
    """任务进入 WAITING_DEPENDENCY。"""

    task_id: str


@dataclass
class TaskUnblocked:
    """依赖满足后任务恢复为 PENDING。"""

    task_id: str


@dataclass
class TaskResumed:
    """用户输入后任务恢复为 RUNNING。"""

    task_id: str
    input_data: Any = None


# ---------------------------------------------------------------------------
# AgentRuntime 进度事件（可观测性）
# ---------------------------------------------------------------------------


@dataclass
class StepProgress:
    """每轮 step_loop 后发布的进度事件。"""

    task_id: str
    step_depth: int
    step_label: Optional[str] = None
    last_message: Optional[str] = None