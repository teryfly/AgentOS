"""
Integration tests for cross-task search functionality.

Tests the result_router scenario and phase_dispatcher scenario.
"""

import pytest

from agent_os.common import MemorySource, MemoryType
from agent_os.memory_center import MemoryCenter


@pytest.mark.asyncio
class TestCrossTaskSearch:
    """Integration tests for cross-task keyword search."""

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

    async def test_result_router_scenario_extract_coding_doc(
        self, memory_center_instance, sample_memory_item
    ):
        """
        Given: architect_session_group completed, wrote LONG memory with has_coding_doc=True
        When: result_router searches with task_id=None
        Then: Can retrieve document from content["final_output"]
        """
        # Simulate architect_session_group completion
        architect_task_id = "architect-task-001"
        architect_memory = sample_memory_item(
            task_id=architect_task_id,
            type_=MemoryType.LONG,
            source=MemorySource.TASK,
            content={
                "task_name": "architect_session_group",
                "result": {
                    "final_output": "# Coding Task Document\n\n## Project: Test\n..."
                }
            },
            metadata={
                "role": "architect_session_group",
                "task_id": architect_task_id,
                "has_coding_doc": True,
            },
            created_at=1700000000000,
        )

        await memory_center_instance.write(architect_memory)

        # result_router searches (different task)
        results = await memory_center_instance.search_by_keyword(
            query="Coding Task Document",
            task_id=None,  # Cross-task search
            top_k=3
        )

        # Filter by metadata (as result_router would do)
        filtered = [
            r for r in results
            if r.source == MemorySource.TASK
            and r.type == MemoryType.LONG
            and r.metadata.get("has_coding_doc") == True
        ]

        assert len(filtered) >= 1
        doc_text = filtered[0].content["result"]["final_output"]
        assert "# Coding Task Document" in doc_text

    async def test_phase_dispatcher_scenario_extract_sub_phases(
        self, memory_center_instance, sample_memory_item
    ):
        """
        Given: engineer_session_group completed, wrote LONG memory with sub_phases
        When: phase_dispatcher searches with task_id=None
        Then: Can retrieve sub-phases JSON
        """
        # Simulate engineer_session_group completion
        engineer_task_id = "engineer-task-001"
        engineer_memory = sample_memory_item(
            task_id=engineer_task_id,
            type_=MemoryType.LONG,
            source=MemorySource.TASK,
            content={
                "task_name": "engineer_session_group",
                "result": {
                    "sub_phases": [
                        {
                            "phase": "Phase 1.1",
                            "description": "Setup",
                            "files": ["setup.py"]
                        },
                        {
                            "phase": "Phase 1.2",
                            "description": "Implementation",
                            "files": ["main.py"]
                        }
                    ]
                }
            },
            metadata={
                "role": "engineer_session_group",
                "task_id": engineer_task_id,
            },
            created_at=1700000000000,
        )

        await memory_center_instance.write(engineer_memory)

        # phase_dispatcher searches
        results = await memory_center_instance.search_by_keyword(
            query="sub_phases",
            task_id=None,  # Cross-task search
            top_k=3
        )

        # Filter by metadata
        filtered = [
            r for r in results
            if r.source == MemorySource.TASK
            and r.type == MemoryType.LONG
        ]

        assert len(filtered) >= 1
        sub_phases = filtered[0].content["result"]["sub_phases"]
        assert len(sub_phases) == 2
        assert sub_phases[0]["phase"] == "Phase 1.1"

    async def test_cross_task_search_respects_top_k(
        self, memory_center_instance, sample_memory_item
    ):
        """
        Given: Many tasks with matching memories
        When: Searching with top_k limit
        Then: Only top_k results are returned
        """
        # Create memories across multiple tasks
        for i in range(10):
            await memory_center_instance.write(
                sample_memory_item(
                    task_id=f"task-{i}",
                    type_=MemoryType.LONG,
                    content={"text": "common keyword in all tasks"},
                    created_at=1000 + i
                )
            )

        results = await memory_center_instance.search_by_keyword(
            query="common keyword",
            task_id=None,
            top_k=3
        )

        assert len(results) == 3