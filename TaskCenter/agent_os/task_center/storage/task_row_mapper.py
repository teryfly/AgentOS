"""
Task <-> PostgreSQL row serialization.

Handles conversion between Task dataclass and asyncpg Record objects.
Manages JSONB serialization for complex fields.
"""
import json
import uuid
from typing import Any
from agent_os.common import Task, TaskStatus, TaskResult


class TaskRowMapper:
    """
    Bidirectional mapper between Task dataclass and database rows.

    Notes:
    - Mapper itself does not enforce UUID validity for Task.id.
    - UUID validation/conversion is handled in store layer where needed.
    """

    @staticmethod
    def to_row(task: Task) -> dict[str, Any]:
        """
        Convert Task to database row dict.

        Args:
            task: Task instance

        Returns:
            Dict suitable for asyncpg parameter binding
        """
        result_json = None
        if task.result:
            result_json = json.dumps(
                {
                    "success": task.result.success,
                    "data": task.result.data,
                    "error": task.result.error,
                }
            )

        return {
            "id": task.id,  # Keep original id shape; store layer handles UUID conversion.
            "name": task.name,
            "description": task.description,
            "role": task.role,
            "status": task.status.value,
            "depends_on": json.dumps(task.depends_on),
            "children": json.dumps(task.children),
            "result": result_json,
            "metadata": json.dumps(task.metadata),
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "version": task.version,
        }

    @staticmethod
    def from_row(row: Any) -> Task:
        """
        Convert database row to Task instance.

        Args:
            row: asyncpg Record object

        Returns:
            Task instance
        """
        result = None
        if row["result"]:
            result_data = json.loads(row["result"]) if isinstance(row["result"], str) else row["result"]
            result = TaskResult(
                success=result_data["success"],
                data=result_data.get("data"),
                error=result_data.get("error"),
            )

        depends_on = row["depends_on"]
        if isinstance(depends_on, str):
            depends_on = json.loads(depends_on)

        children = row["children"]
        if isinstance(children, str):
            children = json.loads(children)

        metadata = row["metadata"]
        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        task_id = row["id"]
        if isinstance(task_id, uuid.UUID):
            task_id = str(task_id)

        return Task(
            id=task_id,
            name=row["name"],
            description=row["description"],
            role=row["role"],
            status=TaskStatus(row["status"]),
            depends_on=depends_on,
            children=children,
            result=result,
            metadata=metadata,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            version=row["version"],
        )