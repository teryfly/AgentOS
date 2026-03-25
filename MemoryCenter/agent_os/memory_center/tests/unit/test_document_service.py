"""
Unit tests for DocumentService.

Tests HTTP-based document queries with mocked httpx client.
"""

from unittest.mock import AsyncMock

import httpx
import pytest

from agent_os.memory_center.document_service import DocumentService


@pytest.mark.asyncio
class TestDocumentService:
    """Tests for DocumentService methods."""

    @pytest.fixture
    def document_service(self, mock_httpx_client, llm_gateway_config):
        """Create DocumentService instance with mocked HTTP client."""
        return DocumentService(
            http_client=mock_httpx_client,
            base_url=llm_gateway_config.base_url,
            token=llm_gateway_config.token,
            project_id=llm_gateway_config.project_id,
        )

    async def test_query_by_ids_concurrent_requests(
        self, document_service, mock_httpx_client, mock_document_response
    ):
        """
        Given: Multiple document IDs
        When: Querying by IDs
        Then: Concurrent GET requests are made and results maintain order
        """
        mock_httpx_client.get.side_effect = [
            AsyncMock(json=lambda: mock_document_response(filename="doc1.md")),
            AsyncMock(json=lambda: mock_document_response(filename="doc2.md")),
            AsyncMock(json=lambda: mock_document_response(filename="doc3.md")),
        ]

        result = await document_service.query_by_ids([1, 2, 3])

        assert len(result) == 3
        assert result[0]["filename"] == "doc1.md"
        assert result[1]["filename"] == "doc2.md"
        assert result[2]["filename"] == "doc3.md"

    async def test_query_by_ids_handles_single_failure(
        self, document_service, mock_httpx_client, mock_document_response
    ):
        """
        Given: Multiple document IDs with one failing
        When: Querying by IDs
        Then: Failed document is skipped, others are returned
        """
        failure_response = AsyncMock()
        failure_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=None, response=None
        )

        mock_httpx_client.get.side_effect = [
            AsyncMock(json=lambda: mock_document_response(filename="doc1.md")),
            failure_response,
            AsyncMock(json=lambda: mock_document_response(filename="doc3.md")),
        ]

        result = await document_service.query_by_ids([1, 2, 3])

        assert len(result) == 2
        assert result[0]["filename"] == "doc1.md"
        assert result[1]["filename"] == "doc3.md"

    async def test_query_by_ids_empty_list(self, document_service):
        """
        Given: Empty document_ids list
        When: Querying by IDs
        Then: Empty list is returned immediately
        """
        result = await document_service.query_by_ids([])

        assert result == []

    async def test_query_by_conditions_with_filters(
        self, document_service, mock_httpx_client
    ):
        """
        Given: Query conditions (filenames, category, query)
        When: Querying by conditions
        Then: POST request is made with correct body
        """
        mock_httpx_client.post.return_value = AsyncMock(
            json=lambda: {
                "documents": [
                    {"filename": "test.md", "content": "...", "version": 1}
                ]
            }
        )

        result = await document_service.query_by_conditions(
            filenames=["test.md"],
            category_id=5,
            query="keyword"
        )

        assert len(result) == 1
        assert result[0]["filename"] == "test.md"

        mock_httpx_client.post.assert_called_once()
        call_kwargs = mock_httpx_client.post.call_args
        assert "json" in call_kwargs.kwargs
        body = call_kwargs.kwargs["json"]
        assert body["filenames"] == ["test.md"]
        assert body["category_id"] == 5
        assert body["query"] == "keyword"

    async def test_query_by_conditions_failure_returns_empty(
        self, document_service, mock_httpx_client
    ):
        """
        Given: Query conditions
        When: HTTP request fails
        Then: Empty list is returned (degradation)
        """
        mock_httpx_client.post.side_effect = httpx.TimeoutException("timeout")

        result = await document_service.query_by_conditions(query="test")

        assert result == []

    async def test_format_documents(self, mock_document_response):
        """
        Given: List of document dicts
        When: Formatting for prompt injection
        Then: Correctly formatted string is returned
        """
        docs = [
            mock_document_response(filename="doc1.md", content="Content 1", version=1),
            mock_document_response(filename="doc2.md", content="Content 2", version=2),
        ]

        result = DocumentService.format_documents(docs)

        assert "## 参考文档" in result
        assert "--- doc1.md (v1) BEGIN ---" in result
        assert "Content 1" in result
        assert "--- doc1.md END ---" in result
        assert "--- doc2.md (v2) BEGIN ---" in result
        assert "Content 2" in result

    async def test_format_documents_empty_list(self):
        """
        Given: Empty document list
        When: Formatting
        Then: Placeholder message is returned
        """
        result = DocumentService.format_documents([])

        assert result == "## 参考文档\n\n(No documents available)"