"""Tests for TMDB constants migration.

This module tests that:
1. TMDB error message constants are correctly defined
2. tmdb_client.py correctly uses constants
3. No hardcoded error messages remain
"""

import pytest


class TestTMDBErrorMessages:
    """Test TMDB error message constants."""

    def test_error_messages_exist(self) -> None:
        """Test that all error messages are defined."""
        from anivault.shared.constants.tmdb_messages import TMDBErrorMessages

        assert hasattr(TMDBErrorMessages, "AUTHENTICATION_FAILED")
        assert hasattr(TMDBErrorMessages, "ACCESS_FORBIDDEN")
        assert hasattr(TMDBErrorMessages, "RATE_LIMIT_EXCEEDED")
        assert hasattr(TMDBErrorMessages, "TIMEOUT")
        assert hasattr(TMDBErrorMessages, "CONNECTION_FAILED")

    def test_operation_names_exist(self) -> None:
        """Test that operation names are defined."""
        from anivault.shared.constants.tmdb_messages import TMDBOperationNames

        assert hasattr(TMDBOperationNames, "SEARCH_TV")
        assert hasattr(TMDBOperationNames, "SEARCH_MOVIE")
        assert hasattr(TMDBOperationNames, "GET_TV_DETAILS")

    def test_messages_not_empty(self) -> None:
        """Test that messages are not empty strings."""
        from anivault.shared.constants.tmdb_messages import TMDBErrorMessages

        assert len(TMDBErrorMessages.AUTHENTICATION_FAILED) > 0
        assert len(TMDBErrorMessages.RATE_LIMIT_EXCEEDED) > 0
        assert len(TMDBErrorMessages.TIMEOUT) > 0


class TestTMDBClientMigration:
    """Test that tmdb_client.py correctly uses constants."""

    def test_tmdb_client_imports_constants(self) -> None:
        """Test that tmdb_client.py imports TMDB constants."""
        from pathlib import Path

        tmdb_file = Path("src/anivault/services/tmdb_client.py")
        content = tmdb_file.read_text(encoding="utf-8")

        assert "from anivault.shared.constants.tmdb_messages import" in content

    def test_tmdb_client_uses_error_messages(self) -> None:
        """Test that tmdb_client.py uses TMDBErrorMessages constants."""
        from pathlib import Path

        tmdb_file = Path("src/anivault/services/tmdb_client.py")
        content = tmdb_file.read_text(encoding="utf-8")

        assert "TMDBErrorMessages.AUTHENTICATION_FAILED" in content
        assert "TMDBErrorMessages.RATE_LIMIT_EXCEEDED" in content
        assert "TMDBErrorMessages.TIMEOUT" in content
        assert "TMDBErrorMessages.CONNECTION_FAILED" in content

    def test_no_hardcoded_error_messages(self) -> None:
        """Test that hardcoded error messages are removed."""
        from pathlib import Path

        tmdb_file = Path("src/anivault/services/tmdb_client.py")
        content = tmdb_file.read_text(encoding="utf-8")

        # Check for specific hardcoded patterns that should be gone
        assert '"TMDB API authentication failed"' not in content
        assert '"TMDB API access forbidden"' not in content
        assert '"TMDB API rate limit exceeded"' not in content
        assert '"TMDB API request timeout"' not in content
        assert '"TMDB API connection failed"' not in content


class TestRollbackHandlerMigration:
    """Test that rollback_handler.py correctly uses constants."""

    def test_rollback_handler_imports_operation_type(self) -> None:
        """Test that rollback_handler.py imports OperationType."""
        from pathlib import Path

        handler_file = Path("src/anivault/cli/rollback_handler.py")
        content = handler_file.read_text(encoding="utf-8")

        assert "from anivault.core.models import OperationType" in content

    def test_rollback_handler_uses_operation_type(self) -> None:
        """Test that rollback_handler.py uses OperationType.MOVE."""
        from pathlib import Path

        handler_file = Path("src/anivault/cli/rollback_handler.py")
        content = handler_file.read_text(encoding="utf-8")

        assert "OperationType.MOVE.value" in content

    def test_no_hardcoded_operation_type(self) -> None:
        """Test that hardcoded 'MOVE' strings in operation_type are removed."""
        from pathlib import Path
        import re

        handler_file = Path("src/anivault/cli/rollback_handler.py")
        content = handler_file.read_text(encoding="utf-8")

        # Check for the specific pattern: "operation_type": "MOVE"
        pattern = r'"operation_type"\s*:\s*"MOVE"'
        matches = re.findall(pattern, content)

        assert len(matches) == 0, f"Found {len(matches)} hardcoded 'MOVE' strings"


class TestOperationType:
    """Test OperationType enum."""

    def test_operation_type_values(self) -> None:
        """Test that OperationType has correct values."""
        from anivault.core.models import OperationType

        assert OperationType.MOVE.value == "move"
        assert OperationType.COPY.value == "copy"

    def test_operation_type_is_enum(self) -> None:
        """Test that OperationType is a string enum."""
        from anivault.core.models import OperationType
        from enum import Enum

        assert issubclass(OperationType, Enum)
        assert issubclass(OperationType, str)

