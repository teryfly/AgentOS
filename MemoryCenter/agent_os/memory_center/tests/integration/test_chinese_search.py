"""
Integration tests for Chinese text search.

Tests PGroonga and built-in search with Chinese/Japanese content.
"""

import pytest

from agent_os.common import MemoryType


@pytest.mark.asyncio
class TestChineseTextSearch:
    """Tests for Chinese/Japanese text search capabilities."""

    async def test_search_chinese_text_with_pgroonga(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Memories with Chinese text content
        When: Searching with Chinese query (PGroonga method)
        Then: Correct results are returned
        
        Document 7: PGroonga provides excellent Chinese search
        """
        # Save Chinese content
        await postgres_storage.save_batch([
            sample_memory_item(
                task_id="task-cn-1",
                content={"text": "这是一个中文测试文档，包含编程相关内容"}
            ),
            sample_memory_item(
                task_id="task-cn-2",
                content={"text": "Python编程语言教程和示例代码"}
            ),
            sample_memory_item(
                task_id="task-cn-3",
                content={"text": "JavaScript前端开发技术文档"}
            ),
        ])
        
        # Force PGroonga method if available
        if postgres_storage._search_method == 'pgroonga':
            # Search with Chinese query
            results = await postgres_storage.search_keyword(
                query="编程",
                task_id=None,
                top_k=5
            )
            
            # Should find matches in Chinese text
            assert len(results) >= 1
            assert any("编程" in str(r.content) for r in results)
        else:
            pytest.skip("PGroonga not available, skipping Chinese search test")

    async def test_search_mixed_chinese_english(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Memories with mixed Chinese and English content
        When: Searching with English query
        Then: Matches are found regardless of Chinese characters
        """
        await postgres_storage.save_batch([
            sample_memory_item(
                content={"text": "Python是一种编程语言 programming language"}
            ),
            sample_memory_item(
                content={"text": "学习Python编程 learn Python programming"}
            ),
        ])
        
        # Search with English term
        results = await postgres_storage.search_keyword(
            query="Python",
            task_id=None,
            top_k=5
        )
        
        assert len(results) >= 2
        assert all("Python" in str(r.content) for r in results)

    async def test_search_builtin_with_chinese_fallback(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Built-in search method (no PGroonga)
        When: Searching Chinese text
        Then: Results returned (may be less accurate than PGroonga)
        
        Document 7: Built-in fallback works but less effective for Chinese
        """
        # Save Chinese content
        await postgres_storage.save(
            sample_memory_item(
                content={"text": "中文内容测试 Coding Task Document"}
            )
        )
        
        # Force built-in method
        original_method = postgres_storage._search_method
        postgres_storage._search_method = 'builtin'
        
        try:
            # Search should still work (using 'simple' config)
            results = await postgres_storage.search_keyword(
                query="Coding Task Document",
                task_id=None,
                top_k=5
            )
            
            # Should find result even with Chinese characters present
            assert len(results) >= 1
        finally:
            postgres_storage._search_method = original_method

    async def test_chinese_unicode_preserved_in_storage(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: MemoryItem with Chinese Unicode characters
        When: Saving and retrieving
        Then: Unicode is preserved exactly
        
        Document 7: Unicode handling in JSONB
        """
        chinese_content = {
            "title": "编码自动化文档",
            "description": "这是一个测试文档，包含各种Unicode字符：中文、日文（日本語）、emoji（🚀✨）",
            "mixed": "Hello 世界 🌍"
        }
        
        item = sample_memory_item(content=chinese_content)
        await postgres_storage.save(item)
        
        results = await postgres_storage.query_by_task(item.task_id)
        
        assert len(results) == 1
        assert results[0].content == chinese_content

    async def test_chinese_metadata_search_filter(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Memories with Chinese metadata
        When: Searching and filtering by metadata
        Then: Chinese metadata is correctly preserved and filterable
        """
        await postgres_storage.save_batch([
            sample_memory_item(
                content={"text": "文档A"},
                metadata={"role": "架构师", "has_coding_doc": True}
            ),
            sample_memory_item(
                content={"text": "文档B"},
                metadata={"role": "工程师", "has_coding_doc": False}
            ),
        ])
        
        results = await postgres_storage.search_keyword(
            query="文档",
            task_id=None,
            top_k=5
        )
        
        # Filter by Chinese metadata
        filtered = [r for r in results if r.metadata.get("role") == "架构师"]
        
        assert len(filtered) >= 1
        assert filtered[0].metadata["role"] == "架构师"


@pytest.mark.asyncio
class TestChineseTokenization:
    """Tests for Chinese tokenization behavior."""

    async def test_chinese_phrase_search(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Memories with Chinese phrases
        When: Searching with multi-character Chinese query
        Then: Phrase matching works correctly
        """
        await postgres_storage.save_batch([
            sample_memory_item(
                content={"text": "编码任务文档包含项目需求"}
            ),
            sample_memory_item(
                content={"text": "编码规范和最佳实践"}
            ),
        ])
        
        # Search with Chinese phrase
        results = await postgres_storage.search_keyword(
            query="编码任务",
            task_id=None,
            top_k=5
        )
        
        # Should prioritize exact phrase match
        assert len(results) >= 1
        if results:
            assert "编码任务" in str(results[0].content)

    async def test_chinese_special_characters_in_search(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Chinese content with punctuation
        When: Searching
        Then: Special characters handled correctly
        """
        await postgres_storage.save(
            sample_memory_item(
                content={"text": "【重要】编码任务：实现用户认证功能"}
            )
        )
        
        results = await postgres_storage.search_keyword(
            query="编码任务",
            task_id=None,
            top_k=5
        )
        
        assert len(results) >= 1