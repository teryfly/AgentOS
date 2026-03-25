"""
Unit tests for CAS retry utility.
"""
import pytest
from agent_os.common import MetadataUpdateConflictError
from agent_os.task_center.state_ops.retry_cas import retry_optimistic
from agent_os.task_center.storage.interfaces import VersionConflict


class TestRetryCAS:
    """Test optimistic lock retry mechanism."""
    
    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """Operation succeeding immediately should not retry."""
        call_count = 0
        
        async def operation():
            nonlocal call_count
            call_count += 1
        
        await retry_optimistic(operation, max_retries=3, conflict_exception_type=MetadataUpdateConflictError)
        
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_success_after_retry(self):
        """Operation succeeding on 2nd attempt should retry once."""
        call_count = 0
        
        async def operation():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise VersionConflict("Simulated conflict")
        
        await retry_optimistic(operation, max_retries=3, conflict_exception_type=MetadataUpdateConflictError)
        
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_exhausts_retries_raises_exception(self):
        """Operation failing all retries should raise conflict exception."""
        call_count = 0
        
        async def operation():
            nonlocal call_count
            call_count += 1
            raise VersionConflict("Persistent conflict")
        
        with pytest.raises(MetadataUpdateConflictError):
            await retry_optimistic(operation, max_retries=3, conflict_exception_type=MetadataUpdateConflictError)
        
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_non_version_conflict_propagates(self):
        """Non-VersionConflict exceptions should propagate immediately."""
        call_count = 0
        
        async def operation():
            nonlocal call_count
            call_count += 1
            raise ValueError("Different error")
        
        with pytest.raises(ValueError):
            await retry_optimistic(operation, max_retries=3, conflict_exception_type=MetadataUpdateConflictError)
        
        assert call_count == 1