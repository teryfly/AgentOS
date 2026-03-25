"""
Mock agent_os.common module for standalone testing.

This allows running tests before agent_os.common is fully set up.
Use real agent_os.common in production.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable
from abc import ABC, abstractmethod


# Enums
class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING_INPUT = "WAITING_INPUT"
    WAITING_DEPENDENCY = "WAITING_DEPENDENCY"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# Models
@dataclass
class TaskResult:
    success: bool
    data: Any
    error: str | None = None


@dataclass
class Task:
    id: str
    name: str
    description: str
    role: str
    status: TaskStatus
    depends_on: list[str] = field(default_factory=list)
    children: list[str] = field(default_factory=list)
    result: TaskResult | None = None
    metadata: dict = field(default_factory=dict)
    created_at: int = 0
    updated_at: int = 0
    version: int = 0


@dataclass
class TaskBatchItem:
    ref_id: str
    name: str
    description: str
    role: str
    depends_on_refs: list[str] = field(default_factory=list)
    depends_on_ids: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class TaskRuntimeState:
    task_id: str
    runtime_data: dict = field(default_factory=dict)
    version: int = 0
    updated_at: int = 0


# Exceptions
class TaskNotFoundError(Exception):
    pass


class InvalidStatusTransitionError(Exception):
    pass


class InvalidTaskStateError(Exception):
    pass


class MetadataUpdateConflictError(Exception):
    pass


class RuntimeStateUpdateConflictError(Exception):
    pass


class CircularDependencyError(Exception):
    pass


class DependencyNotFoundError(Exception):
    pass


class MaxDepthExceededError(Exception):
    pass


class DuplicateRefIdError(Exception):
    pass


# Events
@dataclass
class TaskCreated:
    task_id: str
    name: str
    role: str
    status: TaskStatus


@dataclass
class TaskStarted:
    task_id: str


@dataclass
class TaskCompleted:
    task_id: str
    result: TaskResult


@dataclass
class TaskFailed:
    task_id: str
    error: str


@dataclass
class TaskWaitingInput:
    task_id: str


@dataclass
class TaskWaitingDependency:
    task_id: str


@dataclass
class TaskUnblocked:
    task_id: str


@dataclass
class TaskResumed:
    task_id: str
    input_data: Any


# EventBus Interface
class EventBus(ABC):
    """Abstract EventBus interface."""
    
    @abstractmethod
    async def publish(self, event: Any) -> None:
        pass
    
    @abstractmethod
    def subscribe(self, event_type: type, handler: Callable[[Any], Awaitable[None]]) -> None:
        pass


# InMemoryEventBus Implementation
class InMemoryEventBus(EventBus):
    def __init__(self):
        self.published_events = []
        self.subscribers = {}
    
    async def publish(self, event: Any) -> None:
        self.published_events.append(event)
        event_type = type(event)
        handlers = self.subscribers.get(event_type, [])
        for handler in handlers:
            await handler(event)
    
    def subscribe(self, event_type: type, handler: Callable[[Any], Awaitable[None]]) -> None:
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
    
    def get_events_by_type(self, event_type: type):
        return [e for e in self.published_events if isinstance(e, event_type)]


# Module-level namespace for interfaces
class interfaces:
    EventBus = EventBus


class events:
    TaskCreated = TaskCreated
    TaskStarted = TaskStarted
    TaskCompleted = TaskCompleted
    TaskFailed = TaskFailed
    TaskWaitingInput = TaskWaitingInput
    TaskWaitingDependency = TaskWaitingDependency
    TaskUnblocked = TaskUnblocked
    TaskResumed = TaskResumed