"""
Unit tests for configuration validation edge cases.

Tests environment variable validation, DSN building, and error handling.
"""

import os
import pytest
from unittest.mock import patch


class TestEnvironmentVariableValidation:
    """Tests for _validate_env_vars() edge cases."""

    def test_single_missing_env_var_raises_error(self):
        """
        Given: One required env var missing
        When: Creating MemoryCenter from env
        Then: ValueError with specific var name
        """
        from agent_os.memory_center.config import _validate_env_vars
        
        with patch.dict(os.environ, {
            'DB_NAME': 'test_db',
            'DB_USER': 'test_user',
            'DB_PASSWORD': 'test_pass',
            'CHAT_BACKEND_URL': 'http://test',
            'API_KEY': 'test_key',
            # Missing: CHAT_BACKEND_PROJECT_ID
        }, clear=True):
            with pytest.raises(ValueError) as exc_info:
                _validate_env_vars()
            
            assert "CHAT_BACKEND_PROJECT_ID" in str(exc_info.value)

    def test_multiple_missing_env_vars_lists_all(self):
        """
        Given: Multiple required env vars missing
        When: Validating environment
        Then: ValueError lists all missing vars
        
        Coverage: config.py lines 78-79 (multiple missing vars)
        """
        from agent_os.memory_center.config import _validate_env_vars
        
        with patch.dict(os.environ, {
            'DB_NAME': 'test_db',
            # Missing: DB_USER, DB_PASSWORD, CHAT_BACKEND_URL, API_KEY, CHAT_BACKEND_PROJECT_ID
        }, clear=True):
            with pytest.raises(ValueError) as exc_info:
                _validate_env_vars()
            
            error_msg = str(exc_info.value)
            assert "DB_USER" in error_msg
            assert "DB_PASSWORD" in error_msg
            assert "CHAT_BACKEND_URL" in error_msg
            assert "API_KEY" in error_msg
            assert "CHAT_BACKEND_PROJECT_ID" in error_msg

    def test_all_required_vars_present_no_error(self):
        """
        Given: All required env vars present
        When: Validating environment
        Then: No exception is raised
        """
        from agent_os.memory_center.config import _validate_env_vars
        
        with patch.dict(os.environ, {
            'DB_NAME': 'test_db',
            'DB_USER': 'test_user',
            'DB_PASSWORD': 'test_pass',
            'CHAT_BACKEND_URL': 'http://test',
            'API_KEY': 'test_key',
            'CHAT_BACKEND_PROJECT_ID': '123',
        }, clear=True):
            # Should not raise
            _validate_env_vars()


class TestDSNBuildingEdgeCases:
    """Tests for DSN building from environment variables."""

    def test_dsn_with_special_characters_in_password(self):
        """
        Given: Password with special characters (@, :, /, etc.)
        When: Building DSN from env
        Then: Password is URL-encoded correctly
        
        Document 7: URL-encode password to support special characters
        """
        from agent_os.memory_center.storage import PostgresMemoryStorage
        
        with patch.dict(os.environ, {
            'DB_HOST': 'localhost',
            'DB_PORT': '5432',
            'DB_NAME': 'test_db',
            'DB_USER': 'test_user',
            'DB_PASSWORD': 'p@ss:w/rd?',
        }, clear=True):
            storage = PostgresMemoryStorage()
            dsn = storage._build_dsn_from_env()
            
            # Password should be URL-encoded
            assert 'p%40ss%3Aw%2Frd%3F' in dsn
            assert 'postgresql://test_user:' in dsn
            assert '@localhost:5432/test_db' in dsn

    def test_dsn_uses_default_host_and_port(self):
        """
        Given: DB_HOST and DB_PORT not provided
        When: Building DSN
        Then: Defaults to localhost:5432
        """
        from agent_os.memory_center.storage import PostgresMemoryStorage
        
        with patch.dict(os.environ, {
            'DB_NAME': 'test_db',
            'DB_USER': 'test_user',
            'DB_PASSWORD': 'test_pass',
        }, clear=True):
            storage = PostgresMemoryStorage()
            dsn = storage._build_dsn_from_env()
            
            assert 'localhost:5432' in dsn

    def test_dsn_with_custom_host_and_port(self):
        """
        Given: Custom DB_HOST and DB_PORT provided
        When: Building DSN
        Then: Custom values are used
        """
        from agent_os.memory_center.storage import PostgresMemoryStorage
        
        with patch.dict(os.environ, {
            'DB_HOST': 'db.example.com',
            'DB_PORT': '5433',
            'DB_NAME': 'test_db',
            'DB_USER': 'test_user',
            'DB_PASSWORD': 'test_pass',
        }, clear=True):
            storage = PostgresMemoryStorage()
            dsn = storage._build_dsn_from_env()
            
            assert 'db.example.com:5433' in dsn

    def test_missing_required_db_vars_raises_error(self):
        """
        Given: Required DB env vars missing
        When: Building DSN
        Then: ValueError is raised
        """
        from agent_os.memory_center.storage import PostgresMemoryStorage
        
        with patch.dict(os.environ, {
            'DB_HOST': 'localhost',
            # Missing: DB_NAME, DB_USER, DB_PASSWORD
        }, clear=True):
            with pytest.raises(ValueError) as exc_info:
                PostgresMemoryStorage()
            
            error_msg = str(exc_info.value)
            assert "DB_NAME" in error_msg or "DB_USER" in error_msg or "DB_PASSWORD" in error_msg


class TestBooleanParsing:
    """Tests for _parse_bool() function."""

    def test_parse_bool_true_values(self):
        """
        Given: Various true string values
        When: Parsing boolean
        Then: Returns True
        """
        from agent_os.memory_center.config import _parse_bool
        
        assert _parse_bool("true") is True
        assert _parse_bool("True") is True
        assert _parse_bool("TRUE") is True
        assert _parse_bool("yes") is True
        assert _parse_bool("Yes") is True
        assert _parse_bool("1") is True
        assert _parse_bool("on") is True
        assert _parse_bool("ON") is True

    def test_parse_bool_false_values(self):
        """
        Given: Various false string values
        When: Parsing boolean
        Then: Returns False
        """
        from agent_os.memory_center.config import _parse_bool
        
        assert _parse_bool("false") is False
        assert _parse_bool("False") is False
        assert _parse_bool("no") is False
        assert _parse_bool("0") is False
        assert _parse_bool("off") is False
        assert _parse_bool("") is False
        assert _parse_bool("random") is False


class TestMemoryConfigFromEnv:
    """Tests for MemoryConfig creation from environment."""

    def test_default_memory_config_values(self):
        """
        Given: Optional memory env vars not set
        When: Creating MemoryConfig from env
        Then: Default values are used (max_items=20, semantic=false)
        """
        from agent_os.memory_center.config import create_memory_center_from_env
        
        with patch.dict(os.environ, {
            'DB_NAME': 'test_db',
            'DB_USER': 'test_user',
            'DB_PASSWORD': 'test_pass',
            'CHAT_BACKEND_URL': 'http://test',
            'API_KEY': 'test_key',
            'CHAT_BACKEND_PROJECT_ID': '123',
        }, clear=True):
            memory_center = create_memory_center_from_env()
            
            assert memory_center._config.max_items_per_context == 20
            assert memory_center._config.semantic_search_enabled is False

    def test_custom_memory_config_from_env(self):
        """
        Given: MEMORY_MAX_ITEMS and MEMORY_SEMANTIC_ENABLED set
        When: Creating MemoryCenter from env
        Then: Custom values are used
        """
        from agent_os.memory_center.config import create_memory_center_from_env
        
        with patch.dict(os.environ, {
            'DB_NAME': 'test_db',
            'DB_USER': 'test_user',
            'DB_PASSWORD': 'test_pass',
            'CHAT_BACKEND_URL': 'http://test',
            'API_KEY': 'test_key',
            'CHAT_BACKEND_PROJECT_ID': '123',
            'MEMORY_MAX_ITEMS': '50',
            'MEMORY_SEMANTIC_ENABLED': 'true',
        }, clear=True):
            memory_center = create_memory_center_from_env()
            
            assert memory_center._config.max_items_per_context == 50
            assert memory_center._config.semantic_search_enabled is True