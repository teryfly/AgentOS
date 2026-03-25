"""
Document service for querying knowledge-base documents from chat_backend.

This module provides HTTP-based document queries with:
- Concurrent requests using asyncio.gather
- Failure isolation (single document failure doesn't stop others)
- Document formatting for prompt injection
"""

import asyncio
import inspect
import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class DocumentService:
    """
    HTTP-based document query service.

    This service is the unified entry point for accessing knowledge-base
    documents from chat_backend. It supports:
    - Query by document IDs (concurrent GET requests)
    - Query by conditions (POST request with filters)
    - Document formatting for prompt injection

    All failures are handled gracefully - single document failures are logged
    but don't stop the overall operation.
    """

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        base_url: str,
        token: str,
        project_id: int,
    ) -> None:
        """
        Initialize document service.

        Args:
            http_client: Async HTTP client for making requests
            base_url: Base URL of chat_backend (e.g., http://localhost:8000/v1)
            token: Bearer token for authentication
            project_id: Project ID for document queries
        """
        self._client = http_client
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._project_id = project_id
        self._headers = {"Authorization": f"Bearer {token}"}

    async def _raise_for_status(self, response: Any) -> None:
        """
        Call response.raise_for_status() in a way that supports both:
        - standard httpx.Response (sync method)
        - AsyncMock-based test doubles (async method)
        """
        raise_for_status = getattr(response, "raise_for_status", None)
        if not callable(raise_for_status):
            return

        result = raise_for_status()
        if inspect.isawaitable(result):
            await result

    async def _response_json(self, response: Any) -> Any:
        """
        Read response JSON from both sync and async-compatible test doubles.
        """
        json_method = getattr(response, "json", None)
        if not callable(json_method):
            return None

        data = json_method()
        if inspect.isawaitable(data):
            return await data
        return data

    async def query_by_ids(self, document_ids: list[int]) -> list[dict[str, Any]]:
        """
        Query documents by ID list with concurrent requests.

        Args:
            document_ids: List of plan_documents.id values

        Returns:
            List of document dicts with keys: filename, content, version
            Order matches input document_ids (missing IDs are skipped)

        Note:
            Uses asyncio.gather for concurrent requests.
            Single document failures are logged but don't stop others.
            Final result maintains input order, excluding failed documents.
        """
        if not document_ids:
            return []

        async def _fetch_one(doc_id: int) -> Optional[dict[str, Any]]:
            """Fetch a single document by ID."""
            try:
                url = f"{self._base_url}/plan/documents/{doc_id}"
                resp = await self._client.get(url, headers=self._headers)
                await self._raise_for_status(resp)

                payload = await self._response_json(resp)
                if isinstance(payload, dict):
                    return payload
                return None
            except Exception as e:
                logger.warning(f"Document query failed for id {doc_id}: {e}")
                return None

        tasks = [asyncio.create_task(_fetch_one(doc_id)) for doc_id in document_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        doc_map: dict[int, dict[str, Any]] = {}
        for doc_id, result in zip(document_ids, results):
            if isinstance(result, dict):
                doc_map[doc_id] = result
            elif isinstance(result, Exception):
                logger.warning(f"Exception when fetching document {doc_id}: {result}")

        return [doc_map[doc_id] for doc_id in document_ids if doc_id in doc_map]

    async def query_by_conditions(
        self,
        filenames: Optional[list[str]] = None,
        category_id: int = 5,
        query: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Query documents by conditions (filenames, category, keyword).

        Args:
            filenames: Optional list of filenames for exact match
            category_id: Document category (default 5 for knowledge-base)
            query: Optional keyword for fuzzy search

        Returns:
            List of document dicts with keys: filename, content, version

        Note:
            Uses POST /v1/plan/documents/query with JSON body.
            All failures return empty list (degradation).
        """
        try:
            url = f"{self._base_url}/plan/documents/query"
            body: dict[str, Any] = {
                "project_id": self._project_id,
                "category_id": category_id,
            }

            if filenames:
                body["filenames"] = filenames
            if query:
                body["query"] = query

            resp = await self._client.post(url, json=body, headers=self._headers)
            await self._raise_for_status(resp)

            data = await self._response_json(resp)
            if isinstance(data, dict):
                documents = data.get("documents", [])
                if isinstance(documents, list):
                    return documents
            return []
        except Exception as e:
            logger.warning(f"Document query by conditions failed: {e}")
            return []

    @staticmethod
    def format_documents(docs: list[dict[str, Any]]) -> str:
        """
        Format documents for prompt injection.

        Args:
            docs: List of document dicts with keys: filename, content, version

        Returns:
            Formatted string for prompt injection.
        """
        if not docs:
            return "## 参考文档\n\n(No documents available)"

        lines = ["## 参考文档\n"]
        for doc in docs:
            filename = doc.get("filename", "unknown")
            version = doc.get("version", 1)
            content = doc.get("content", "")
            lines.append(f"--- {filename} (v{version}) BEGIN ---")
            lines.append(content)
            lines.append(f"--- {filename} END ---\n")

        return "\n".join(lines)