"""
Unit tests for StateMachine pure logic.
"""
import pytest
from agent_os.common import TaskStatus, InvalidStatusTransitionError
from agent_os.task_center.state_machine import validate_transition, determine_initial_status, VALID_TRANSITIONS


class TestValidateTransition:
    """Test state transition validation."""
    
    def test_all_legal_transitions_pass(self):
        """All defined legal transitions should pass validation."""
        for current, allowed_targets in VALID_TRANSITIONS.items():
            for target in allowed_targets:
                # Should not raise
                validate_transition(current, target)
    
    def test_illegal_transition_raises_error(self):
        """Illegal transitions should raise InvalidStatusTransitionError."""
        with pytest.raises(InvalidStatusTransitionError):
            validate_transition(TaskStatus.PENDING, TaskStatus.COMPLETED)
    
    def test_terminal_states_reject_all_transitions(self):
        """COMPLETED and FAILED cannot transition to any state."""
        with pytest.raises(InvalidStatusTransitionError):
            validate_transition(TaskStatus.COMPLETED, TaskStatus.RUNNING)
        
        with pytest.raises(InvalidStatusTransitionError):
            validate_transition(TaskStatus.FAILED, TaskStatus.RUNNING)
    
    def test_completed_to_completed_is_illegal(self):
        """Self-transition on terminal state is illegal."""
        with pytest.raises(InvalidStatusTransitionError):
            validate_transition(TaskStatus.COMPLETED, TaskStatus.COMPLETED)
    
    def test_waiting_dependency_to_running_is_illegal(self):
        """Direct transition from WAITING_DEPENDENCY to RUNNING is illegal."""
        with pytest.raises(InvalidStatusTransitionError):
            validate_transition(TaskStatus.WAITING_DEPENDENCY, TaskStatus.RUNNING)


class TestDetermineInitialStatus:
    """Test initial status determination logic."""
    
    def test_no_dependencies_returns_pending(self):
        """Task with no dependencies should be PENDING."""
        result = determine_initial_status([])
        assert result == TaskStatus.PENDING
    
    def test_all_dependencies_completed_returns_pending(self):
        """Task with all completed dependencies should be PENDING."""
        dep_statuses = [TaskStatus.COMPLETED, TaskStatus.COMPLETED, TaskStatus.COMPLETED]
        result = determine_initial_status(dep_statuses)
        assert result == TaskStatus.PENDING
    
    def test_some_dependencies_incomplete_returns_waiting_dependency(self):
        """Task with incomplete dependencies should be WAITING_DEPENDENCY."""
        dep_statuses = [TaskStatus.COMPLETED, TaskStatus.RUNNING, TaskStatus.COMPLETED]
        result = determine_initial_status(dep_statuses)
        assert result == TaskStatus.WAITING_DEPENDENCY
    
    def test_all_dependencies_pending_returns_waiting_dependency(self):
        """Task depending on pending tasks should be WAITING_DEPENDENCY."""
        dep_statuses = [TaskStatus.PENDING, TaskStatus.PENDING]
        result = determine_initial_status(dep_statuses)
        assert result == TaskStatus.WAITING_DEPENDENCY
    
    def test_single_failed_dependency_returns_waiting_dependency(self):
        """Even failed dependencies block task."""
        dep_statuses = [TaskStatus.FAILED]
        result = determine_initial_status(dep_statuses)
        assert result == TaskStatus.WAITING_DEPENDENCY