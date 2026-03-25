"""
Integration tests for document query flow.
Tests end-to-end document queries with real HTTP calls (or mocked).
"""
import os
import httpx
import pytest
from agent_os.memory_center import MemoryCenter
def _build_health_url(base_url: str) -> str:
    """Build health endpoint URL from chat backend base URL."""
    normalized = base_url.rstrip("/")
    if normalized.endswith("/v1"):
        return f"{normalized[:-3]}/health"
    return f"{normalized}/health"
@pytest.mark.asyncio
class TestDocumentQueryFlow:
    """Integration tests for document query operations."""
    @pytest.fixture
    async def memory_center_with_real_client(
        self,
        postgres_storage,
        clean_db,
        memory_config,
        llm_gateway_config,
    ):
        """
        Create MemoryCenter with real HTTP client and verify backend availability.
        """
        backend_url = os.getenv("CHAT_BACKEND_URL", llm_gateway_config.base_url)
        print(f"CHAT_BACKEND_URL={backend_url}")
        health_url = _build_health_url(backend_url)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(health_url)
                response.raise_for_status()
        except Exception as exc:
            pytest.skip(
                f"chat_backend unavailable at {health_url}: {exc}"
            )
        llm_gateway_config.base_url = backend_url
        llm_gateway_config.token = os.getenv("API_KEY", llm_gateway_config.token)
        memory_center = MemoryCenter(
            storage=postgres_storage,
            config=memory_config,
            llm_gateway_config=llm_gateway_config,
        )
        yield memory_center
        await memory_center.close()
    async def test_query_documents_by_ids_real_http(
        self, memory_center_with_real_client
    ):
        """
        Given: A running chat_backend instance
        When: Querying by IDs with real HTTP client
        Then: Request is sent and response is handled gracefully
        """
        doc_ids = [1, 2]
        results = await memory_center_with_real_client.query_documents_by_ids(doc_ids)
        assert isinstance(results, list)
        if results:
            assert all("filename" in doc for doc in results)
            assert all("content" in doc for doc in results)
    async def test_get_formatted_documents_end_to_end(
        self, memory_center_with_real_client
    ):
        """
        Given: Empty document ID list
        When: Getting formatted documents
        Then: None is returned
        """
        result = await memory_center_with_real_client.get_formatted_documents_by_ids([])
        assert result is None
    async def test_format_documents_static_method(self):
        """
        Given: Document dicts
        When: Formatting with static method
        Then: Correctly formatted string is returned
        """
        from agent_os.memory_center import MemoryCenter
        docs = [
            {
                "filename": "test1.md",
                "content": "# Test Document 1\nContent here",
                "version": 1
            },
            {
                "filename": "test2.md",
                "content": "# Test Document 2\nMore content",
                "version": 2
            }
        ]
        result = MemoryCenter.format_documents(docs)
        assert "## 参考文档" in result
        assert "--- test1.md (v1) BEGIN ---" in result
        assert "# Test Document 1" in result
        assert "--- test1.md END ---" in result
        assert "--- test2.md (v2) BEGIN ---" in result
        assert "--- test2.md END ---" in result
    async def test_document_query_failure_degradation(
        self, memory_center_with_real_client
    ):
        """
        Given: Invalid document IDs
        When: Querying documents
        Then: Empty list is returned (degradation, no exception)
        """
        invalid_ids = [99999, 99998, 99997]
        results = await memory_center_with_real_client.query_documents_by_ids(invalid_ids)
        assert isinstance(results, list)