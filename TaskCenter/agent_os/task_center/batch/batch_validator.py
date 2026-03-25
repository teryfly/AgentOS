"""
Batch-level constraint validation.

Checks ref_id uniqueness and external dependency existence.
"""
import logging
from agent_os.common import TaskBatchItem, DuplicateRefIdError, DependencyNotFoundError

logger = logging.getLogger(__name__)


class BatchValidator:
    """
    Validates batch creation constraints.
    """
    
    def __init__(self, task_store):
        """
        Args:
            task_store: TaskStore instance for querying existing tasks
        """
        self._task_store = task_store
    
    @staticmethod
    def check_ref_uniqueness(items: list[TaskBatchItem]) -> None:
        """
        Check for duplicate ref_ids in batch.
        
        Args:
            items: Batch items
            
        Raises:
            DuplicateRefIdError: Duplicate ref_id found
        """
        seen = set()
        for item in items:
            if item.ref_id in seen:
                raise DuplicateRefIdError(f"Duplicate ref_id in batch: {item.ref_id}")
            seen.add(item.ref_id)
    
    async def check_external_deps_exist(self, external_deps: set[str]) -> None:
        """
        Verify all external dependency task_ids exist.
        
        Args:
            external_deps: Set of task_ids referenced by depends_on_ids
            
        Raises:
            DependencyNotFoundError: Referenced task does not exist
        """
        for dep_id in external_deps:
            try:
                await self._task_store.get(dep_id)
            except Exception:
                raise DependencyNotFoundError(f"Dependency task {dep_id} not found")