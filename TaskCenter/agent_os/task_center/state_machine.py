"""
Pure state transition validation logic.

Defines legal state transitions and initial status determination.
No side effects or external dependencies.
"""
from agent_os.common import TaskStatus, InvalidStatusTransitionError


# Legal state transitions map
VALID_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.RUNNING},
    TaskStatus.RUNNING: {
        TaskStatus.WAITING_INPUT,
        TaskStatus.WAITING_DEPENDENCY,
        TaskStatus.COMPLETED,
        TaskStatus.FAILED
    },
    TaskStatus.WAITING_INPUT: {TaskStatus.RUNNING},
    TaskStatus.WAITING_DEPENDENCY: {TaskStatus.PENDING},
    TaskStatus.COMPLETED: set(),
    TaskStatus.FAILED: set()
}


def validate_transition(current: TaskStatus, target: TaskStatus) -> None:
    """
    Validate state transition legality.
    
    Args:
        current: Current task status
        target: Desired target status
        
    Raises:
        InvalidStatusTransitionError: Transition is illegal
    """
    allowed = VALID_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidStatusTransitionError(
            f"Invalid transition: {current.value} -> {target.value}"
        )


def determine_initial_status(dep_statuses: list[TaskStatus]) -> TaskStatus:
    """
    Determine initial status for new task based on dependencies.
    
    Args:
        dep_statuses: List of dependency task statuses
        
    Returns:
        PENDING if all dependencies COMPLETED or no dependencies,
        WAITING_DEPENDENCY otherwise
    """
    if not dep_statuses:
        return TaskStatus.PENDING
    
    if all(status == TaskStatus.COMPLETED for status in dep_statuses):
        return TaskStatus.PENDING
    
    return TaskStatus.WAITING_DEPENDENCY