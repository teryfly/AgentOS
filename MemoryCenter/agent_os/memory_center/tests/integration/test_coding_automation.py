"""
Integration tests for coding automation scenarios.

Tests the complete flow of architect → result_router → code_dev_group.
"""

import pytest

from agent_os.common import MemorySource, MemoryType
from agent_os.memory_center import MemoryCenter


@pytest.mark.asyncio
class TestCodingAutomation:
    """Integration tests for coding automation workflows."""

    @pytest.fixture
    async def memory_center_instance(
        self, postgres_storage, memory_config, llm_gateway_config
    ):
        """Create MemoryCenter instance with real storage."""
        return MemoryCenter(
            storage=postgres_storage,
            config=memory_config,
            llm_gateway_config=llm_gateway_config,
        )

    async def test_architect_to_result_router_flow(
        self, memory_center_instance, sample_memory_item
    ):
        """
        Given: architect_session_group completes and writes LONG memory
        When: result_router queries for Coding Task Document
        Then: Document is successfully retrieved and can be parsed
        """
        # Step 1: architect_session_group completes
        architect_task_id = "architect-session-001"
        coding_doc = """# Coding Task Document

**Project:** TestProject
**Version:** v1.0

## Task List

### Task 1: Setup
- Create directory structure
- Initialize configuration

**estimate_n:** 25"""

        architect_memory = sample_memory_item(
            task_id=architect_task_id,
            type_=MemoryType.LONG,
            source=MemorySource.TASK,
            content={
                "task_name": "architect_session_group",
                "result": {"final_output": coding_doc}
            },
            metadata={
                "role": "architect_session_group",
                "task_id": architect_task_id,
                "has_coding_doc": True,
            },
        )

        await memory_center_instance.write(architect_memory)

        # Step 2: result_router searches (different task)
        router_task_id = "result-router-001"
        results = await memory_center_instance.search_by_keyword(
            query="Coding Task Document",
            task_id=None,
            top_k=3
        )

        # Step 3: Filter and extract
        filtered = [
            r for r in results
            if r.source == MemorySource.TASK
            and r.type == MemoryType.LONG
            and r.metadata.get("has_coding_doc") == True
        ]

        assert len(filtered) >= 1
        retrieved_doc = filtered[0].content["result"]["final_output"]
        assert "# Coding Task Document" in retrieved_doc
        assert "estimate_n:" in retrieved_doc

    async def test_engineer_to_phase_dispatcher_flow(
        self, memory_center_instance, sample_memory_item
    ):
        """
        Given: engineer_session_group completes with sub-phases
        When: phase_dispatcher queries for sub_phases
        Then: Sub-phases are successfully retrieved and can be processed
        """
        # Step 1: engineer_session_group completes
        engineer_task_id = "engineer-session-001"
        sub_phases_data = [
            {
                "phase": "Phase 1.1",
                "description": "Database schema",
                "files": ["schema.sql", "migrations/001.sql"]
            },
            {
                "phase": "Phase 1.2",
                "description": "API implementation",
                "files": ["api/routes.py", "api/models.py"]
            }
        ]

        engineer_memory = sample_memory_item(
            task_id=engineer_task_id,
            type_=MemoryType.LONG,
            source=MemorySource.TASK,
            content={
                "task_name": "engineer_session_group",
                "result": {"sub_phases": sub_phases_data}
            },
            metadata={
                "role": "engineer_session_group",
                "task_id": engineer_task_id,
            },
        )

        await memory_center_instance.write(engineer_memory)

        # Step 2: phase_dispatcher searches
        dispatcher_task_id = "phase-dispatcher-001"
        results = await memory_center_instance.search_by_keyword(
            query="sub_phases engineer",
            task_id=None,
            top_k=3
        )

        # Step 3: Extract sub_phases
        filtered = [
            r for r in results
            if r.source == MemorySource.TASK
            and r.type == MemoryType.LONG
        ]

        assert len(filtered) >= 1
        retrieved_phases = filtered[0].content["result"]["sub_phases"]
        assert len(retrieved_phases) == 2
        assert retrieved_phases[0]["phase"] == "Phase 1.1"
        assert len(retrieved_phases[1]["files"]) == 2

    async def test_code_dev_group_memory_writes(
        self, memory_center_instance, sample_memory_item
    ):
        """
        Given: code_dev_group executing steps
        When: Tool results are written as SHORT memories
        Then: Memories are correctly persisted and can be used for context
        """
        task_id = "code-dev-group-001"

        # Simulate tool execution writing SHORT memories
        tool_memories = [
            sample_memory_item(
                task_id=task_id,
                type_=MemoryType.SHORT,
                source=MemorySource.TOOL,
                content={"tool": "code_execute", "step": 1, "result": "PASS"},
                metadata={"tool_name": "code_execute", "dry_run": True},
                created_at=1000
            ),
            sample_memory_item(
                task_id=task_id,
                type_=MemoryType.SHORT,
                source=MemorySource.TOOL,
                content={"tool": "code_execute", "step": 2, "result": "PASS"},
                metadata={"tool_name": "code_execute", "dry_run": False},
                created_at=2000
            ),
        ]

        await memory_center_instance.write_batch(tool_memories)

        # Build context for next iteration
        context = await memory_center_instance.build_context(task_id)

        assert len(context.items) == 2
        assert all(item.source == MemorySource.TOOL for item in context.items)
        assert context.items[0].created_at == 2000  # Newest first