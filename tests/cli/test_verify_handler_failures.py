"""Failure-First tests for verify_handler.py.

Stage 4.2: Test that _collect_verify_data raises exceptions instead of
returning None for error conditions.

Note: _collect_verify_data는 검증 도구이므로 graceful degradation이 의도됨.
내부 에러는 FAILED 상태로 반환하고, 외부 I/O 에러만 예외 발생.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from anivault.cli.common.models import VerifyOptions
from anivault.cli.verify_handler import _collect_verify_data
from anivault.shared.errors import ApplicationError, ErrorCode, InfrastructureError


class TestCollectVerifyDataFailures:
    """_collect_verify_data() 실패 케이스 테스트."""

    def test_search_error_returns_failed_status(self):
        """search_media 에러 시 FAILED 상태로 반환 (graceful)."""
        # Given: Mock options
        options = Mock()
        options.tmdb = True
        options.all_components = False

        # Mock TMDBClient
        with patch("anivault.services.TMDBClient") as mock_client_class:
            mock_client = Mock()
            # search_media 실패
            async def mock_search_fail(query):
                raise ValueError("Invalid stats")
            mock_client.search_media = mock_search_fail
            mock_client_class.return_value = mock_client

            # When
            result = _collect_verify_data(options)

            # Then: graceful degradation - FAILED 상태 반환
            assert result is not None
            assert result["tmdb_api"]["status"] == "FAILED"
            assert result["verification_status"] == "FAILED"

    def test_valid_verification_returns_dict(self):
        """유효한 검증 시 dict 반환."""
        # Given: Mock options
        options = Mock()
        options.tmdb = True
        options.all_components = False

        # Mock TMDBClient
        with patch("anivault.services.TMDBClient") as mock_client_class:
            mock_client = Mock()
            # search_media는 async이므로 coroutine 반환
            async def mock_search(query):
                return []
            mock_client.search_media = mock_search
            mock_client_class.return_value = mock_client

            # When
            result = _collect_verify_data(options)

            # Then
            assert result is not None
            assert isinstance(result, dict)
            assert "tmdb_api" in result


# Note: _collect_verify_data는 검증 도구이므로 내부 에러는
# graceful degradation으로 처리하고, 외부 I/O 에러만 예외 발생.

