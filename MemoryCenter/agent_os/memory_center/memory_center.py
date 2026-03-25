"""
MemoryCenter facade - public interface for memory management.

This module provides the main MemoryCenter class that:
- Wraps all storage operations with error handling
- Integrates context assembly and document services
- Provides a clean API for other modules (AgentRuntime, ContextBuilder, etc.)
- Ensures failures degrade gracefully without stopping main flow
"""

import logging
from typing import Optional

import httpx

from agent_os.common import (
    LlmGatewayConfig,
    MemoryConfig,
    MemoryContext,
    MemoryItem,
    MemoryType,
    SemanticSearchNotEnabledError,
)

from .context_assembler import assemble_context
from .document_service import DocumentService
from .storage.base import MemoryStorage

logger = logging.getLogger(__name__)


class MemoryCenter:
    """
    Unified memory management facade.
    
    This class is the public interface for all memory operations:
    - CRUD operations on memories (write, read, delete)
    - Context building for task execution
    - Keyword and semantic search
    - Knowledge-base document queries and formatting
    
    Key features:
    - All storage failures are caught and logged (write failures don't propagate)
    - Read failures return empty lists (degradation)
    - Document query failures are isolated (single doc failure doesn't stop others)
    - All public methods are async
    
    Lifecycle:
    - Call storage.initialize() after construction
    - Call close() during system shutdown
    """

    def __init__(
        self,
        storage: MemoryStorage,
        config: MemoryConfig,
        llm_gateway_config: LlmGatewayConfig,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        """
        Initialize MemoryCenter.
        
        Args:
            storage: Storage implementation (must be initialized separately)
            config: Memory configuration (max items, search settings, etc.)
            llm_gateway_config: LLM gateway config for document service
            http_client: Optional HTTP client. If None, creates a new one.
                        If provided, caller is responsible for closing it.
        """
        self._storage = storage
        self._config = config
        
        # Create document service for knowledge-base queries
        client = http_client or httpx.AsyncClient(timeout=30.0)
        self._document_service = DocumentService(
            http_client=client,
            base_url=llm_gateway_config.base_url,
            token=llm_gateway_config.token,
            project_id=llm_gateway_config.project_id,
        )
        
        # Track whether we own the HTTP client (for cleanup)
        self._http_client_owned = http_client is None

    # ========== Memory CRUD ==========

    async def write(self, memory: MemoryItem) -> None:
        """
        Write a single memory item.
        
        Args:
            memory: MemoryItem to persist
            
        Note:
            Failures are logged but never propagate.
            This ensures memory write failures don't interrupt main execution flow.
        """
        try:
            await self._storage.save(memory)
        except Exception as e:
            logger.warning(
                f"MemoryCenter.write failed for task {memory.task_id}: {e}"
            )

    async def write_batch(self, memories: list[MemoryItem]) -> None:
        """
        Write multiple memory items in a batch.
        
        Args:
            memories: List of MemoryItem instances to persist
            
        Note:
            Best-effort operation. Partial failures are logged.
            Never propagates exceptions.
        """
        if not memories:
            return

        try:
            await self._storage.save_batch(memories)
        except Exception as e:
            logger.warning(f"MemoryCenter.write_batch failed: {e}")

    async def get_by_task(
        self,
        task_id: str,
        types: Optional[list[MemoryType]] = None
    ) -> list[MemoryItem]:
        """
        Retrieve memories for a task, optionally filtered by type.
        
        Args:
            task_id: Task identifier
            types: Optional list of MemoryType to filter by
            
        Returns:
            List of MemoryItem instances (empty on failure)
            
        Note:
            Failures return empty list (degradation).
            Never propagates exceptions.
        """
        try:
            return await self._storage.query_by_task(task_id, types)
        except Exception as e:
            logger.error(f"MemoryCenter.get_by_task failed for {task_id}: {e}")
            return []

    async def delete(self, memory_id: str) -> None:
        """
        Delete a specific memory by ID.
        
        Args:
            memory_id: Unique identifier of the memory to delete
            
        Note:
            Failures are logged but never propagate.
        """
        try:
            await self._storage.delete(memory_id)
        except Exception as e:
            logger.warning(f"MemoryCenter.delete failed for {memory_id}: {e}")

    async def delete_by_task(
        self,
        task_id: str,
        types: Optional[list[MemoryType]] = None
    ) -> None:
        """
        Delete all memories for a task, optionally filtered by type.
        
        Args:
            task_id: Task identifier
            types: Optional list of MemoryType to delete
            
        Note:
            Failures are logged but never propagate.
            Typically used to clean up SHORT memories after task completion.
        """
        try:
            await self._storage.delete_by_task(task_id, types)
        except Exception as e:
            logger.warning(
                f"MemoryCenter.delete_by_task failed for {task_id}: {e}"
            )

    # ========== Search Operations ==========

    async def search_by_keyword(
        self,
        query: str,
        task_id: Optional[str] = None,
        top_k: int = 5
    ) -> list[MemoryItem]:
        """
        Keyword search in memory content.
        
        Args:
            query: Search query string
            task_id: Optional task scope. If None, performs cross-task search.
            top_k: Maximum number of results
            
        Returns:
            List of MemoryItem instances ordered by relevance (empty on failure)
            
        Note:
            When task_id=None, performs global cross-task search.
            This is used by downstream tasks (e.g., result_router) to
            retrieve LONG memories from upstream tasks.
            
            Failures return empty list (degradation).
        """
        try:
            return await self._storage.search_keyword(query, task_id, top_k)
        except Exception as e:
            logger.error(
                f"MemoryCenter.search_by_keyword failed for query '{query}': {e}"
            )
            return []

    async def search_semantic(
        self,
        query: str,
        top_k: int = 5
    ) -> list[MemoryItem]:
        """
        Semantic search in memory content (future feature).
        
        Args:
            query: Search query string
            top_k: Maximum number of results
            
        Returns:
            List of MemoryItem instances ordered by semantic similarity
            
        Raises:
            SemanticSearchNotEnabledError: If semantic search is disabled
            NotImplementedError: Feature not yet implemented
            
        Note:
            This is a placeholder for future vector search implementation.
            Currently always raises an error.
        """
        if not self._config.semantic_search_enabled:
            raise SemanticSearchNotEnabledError(
                "Semantic search is disabled. Enable via MemoryConfig."
            )
        
        # Future implementation: vector embedding + similarity search
        raise NotImplementedError("Semantic search not yet implemented")

    def supports_semantic_search(self) -> bool:
        """
        Check if semantic search is available.
        
        Returns:
            True if semantic_search_enabled in config, False otherwise
            
        Note:
            Actors should check this before calling search_semantic().
        """
        return self._config.semantic_search_enabled

    # ========== Context Building ==========

    async def build_context(
        self,
        task_id: str,
        include_shared: bool = True,
        query: Optional[str] = None
    ) -> MemoryContext:
        """
        Build memory context for task execution.
        
        Args:
            task_id: Task identifier
            include_shared: Whether to include SHARED type memories
            query: Optional search query (scoped to task_id)
            
        Returns:
            MemoryContext with assembled and truncated memories
            
        Note:
            This is the main entry point for AgentRuntime to get context.
            Failures return minimal context (empty items, not truncated).
            
            The query parameter enables keyword search within the task scope.
            For cross-task search, use search_by_keyword(task_id=None).
        """
        try:
            return await assemble_context(
                self._storage,
                self._config,
                task_id,
                include_shared,
                query
            )
        except Exception as e:
            logger.error(f"MemoryCenter.build_context failed for {task_id}: {e}")
            # Return minimal context on failure
            return MemoryContext(task_id=task_id, items=[], truncated=False)

    # ========== Document Operations ==========

    async def query_documents_by_ids(
        self,
        document_ids: list[int]
    ) -> list[dict]:
        """
        Query knowledge-base documents by ID list.
        
        Args:
            document_ids: List of plan_documents.id values
            
        Returns:
            List of document dicts with keys: filename, content, version
            Order matches input (missing IDs are silently skipped)
            Empty list on failure (degradation)
            
        Note:
            This is the unified entry point for document access.
            ContextBuilder uses this to fetch documents.
            Single document failures don't stop the overall query.
        """
        if not document_ids:
            return []

        try:
            return await self._document_service.query_by_ids(document_ids)
        except Exception as e:
            logger.warning(f"MemoryCenter.query_documents_by_ids failed: {e}")
            return []

    async def query_documents(
        self,
        filenames: Optional[list[str]] = None,
        category_id: int = 5,
        query: Optional[str] = None,
    ) -> list[dict]:
        """
        Query knowledge-base documents by conditions.
        
        Args:
            filenames: Optional list of filenames for exact match
            category_id: Document category (default 5)
            query: Optional keyword for fuzzy search
            
        Returns:
            List of document dicts with keys: filename, content, version
            Empty list on failure (degradation)
            
        Note:
            This is the unified entry point for conditional document queries.
        """
        try:
            return await self._document_service.query_by_conditions(
                filenames, category_id, query
            )
        except Exception as e:
            logger.warning(f"MemoryCenter.query_documents failed: {e}")
            return []

    @staticmethod
    def format_documents(docs: list[dict]) -> str:
        """
        Format documents for prompt injection.
        
        Args:
            docs: List of document dicts
            
        Returns:
            Formatted string suitable for inserting into system prompt
            
        Note:
            This is a static method as it has no dependencies.
            Can be called without a MemoryCenter instance.
        """
        return DocumentService.format_documents(docs)

    async def get_formatted_documents_by_ids(
        self,
        document_ids: list[int]
    ) -> Optional[str]:
        """
        Query and format documents in one call.
        
        Args:
            document_ids: List of plan_documents.id values
            
        Returns:
            Formatted document string, or None if no valid documents found
            
        Note:
            Convenience method for ContextBuilder.
            Returns None (not empty string) when:
            - document_ids is empty
            - All document queries fail
            
            This allows LlmGateway to skip document block injection when None.
        """
        if not document_ids:
            return None

        docs = await self.query_documents_by_ids(document_ids)
        
        if not docs:
            return None

        return self.format_documents(docs)

    # ========== Lifecycle ==========

    async def close(self) -> None:
        """
        Close storage and HTTP client resources.
        
        Note:
            Call this during system shutdown.
            Only closes HTTP client if we created it (not injected).
        """
        await self._storage.close()
        
        if self._http_client_owned:
            await self._document_service._client.aclose()
        
        logger.info("MemoryCenter closed")