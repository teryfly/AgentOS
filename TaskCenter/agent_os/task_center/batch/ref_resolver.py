"""
Reference ID resolution for batch operations.

Maps ref_id to task_id and resolves dependency references.
"""
import logging
import uuid
from agent_os.common import TaskBatchItem

logger = logging.getLogger(__name__)


class RefResolver:
    """
    Resolves ref_id references in batch creation.
    """
    
    @staticmethod
    def generate_id_map(items: list[TaskBatchItem]) -> dict[str, str]:
        """
        Generate task_id for each ref_id.
        
        Args:
            items: Batch items with ref_id
            
        Returns:
            Map of ref_id to generated task_id
        """
        return {item.ref_id: str(uuid.uuid4()) for item in items}
    
    @staticmethod
    def resolve_dependencies(
        item: TaskBatchItem,
        ref_to_id: dict[str, str]
    ) -> list[str]:
        """
        Resolve depends_on_refs to task_ids and merge with depends_on_ids.
        
        Args:
            item: Batch item
            ref_to_id: Map of ref_id to task_id
            
        Returns:
            List of resolved dependency task_ids
        """
        resolved_deps = []
        
        # Resolve ref-based dependencies
        for ref in item.depends_on_refs:
            if ref in ref_to_id:
                resolved_deps.append(ref_to_id[ref])
            else:
                logger.warning(f"[TaskCenter | RefResolver | resolve_dependencies] ref_id {ref} not found in batch")
        
        # Add external dependencies
        resolved_deps.extend(item.depends_on_ids)
        
        return resolved_deps