"""
Fluent API for building test tasks and batch items.
"""
import time
import uuid
from agent_os.common import Task, TaskBatchItem, TaskStatus, TaskResult


class TaskBuilder:
    """Builder for Task instances."""
    
    def __init__(self):
        self._id = str(uuid.uuid4())
        self._name = "Test Task"
        self._description = "Test Description"
        self._role = "test_role"
        self._status = TaskStatus.PENDING
        self._depends_on = []
        self._children = []
        self._result = None
        self._metadata = {}
        self._version = 0
    
    def with_id(self, task_id: str):
        self._id = task_id
        return self
    
    def with_name(self, name: str):
        self._name = name
        return self
    
    def with_role(self, role: str):
        self._role = role
        return self
    
    def with_status(self, status: TaskStatus):
        self._status = status
        return self
    
    def with_depends_on(self, *task_ids: str):
        self._depends_on = list(task_ids)
        return self
    
    def with_metadata(self, metadata: dict):
        self._metadata = metadata
        return self
    
    def with_result(self, success: bool, data=None, error=None):
        self._result = TaskResult(success=success, data=data, error=error)
        return self
    
    def build(self) -> Task:
        current_time = int(time.time() * 1000)
        return Task(
            id=self._id,
            name=self._name,
            description=self._description,
            role=self._role,
            status=self._status,
            depends_on=self._depends_on,
            children=self._children,
            result=self._result,
            metadata=self._metadata,
            created_at=current_time,
            updated_at=current_time,
            version=self._version
        )


class BatchItemBuilder:
    """Builder for TaskBatchItem instances."""
    
    def __init__(self):
        self._ref_id = f"ref_{uuid.uuid4().hex[:8]}"
        self._name = "Batch Task"
        self._description = "Batch Description"
        self._role = "batch_role"
        self._depends_on_refs = []
        self._depends_on_ids = []
        self._metadata = {}
    
    def with_ref_id(self, ref_id: str):
        self._ref_id = ref_id
        return self
    
    def with_name(self, name: str):
        self._name = name
        return self
    
    def with_role(self, role: str):
        self._role = role
        return self
    
    def depends_on_refs(self, *refs: str):
        self._depends_on_refs = list(refs)
        return self
    
    def depends_on_ids(self, *ids: str):
        self._depends_on_ids = list(ids)
        return self
    
    def with_metadata(self, metadata: dict):
        self._metadata = metadata
        return self
    
    def build(self) -> TaskBatchItem:
        return TaskBatchItem(
            ref_id=self._ref_id,
            name=self._name,
            description=self._description,
            role=self._role,
            depends_on_refs=self._depends_on_refs,
            depends_on_ids=self._depends_on_ids,
            metadata=self._metadata
        )