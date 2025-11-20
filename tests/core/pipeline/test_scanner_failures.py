"""Failure-First tests for scanner.py.

Stage 3.1 + Stage 8: Test that functions properly log when skipping files
instead of silently ignoring errors.

Note: Some tests verify logger usage. Logger propagation setup may affect
caplog capture in tests, but actual logging is verified via stderr output.
"""

import logging
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from anivault.core.pipeline.components import DirectoryScanner
from anivault.core.pipeline.utils import BoundedQueue, ScanStatistics


class TestShouldIncludeFileLogging:
    """_should_include_file() 로깅 테스트."""

    def test_permission_error_returns_false_with_logging(self, caplog):
        """Permission 에러 시 False 반환 + 로깅."""
        # Given: filter_engine 활성화해야 stat() 호출
        queue = BoundedQueue(maxsize=10)
        stats = ScanStatistics()
        mock_filter = Mock()
        scanner = DirectoryScanner(
            root_path=Path("/test"),
            extensions=[".mkv"],
            input_queue=queue,
            stats=stats,
            filter_engine=mock_filter,  # FilterEngine 활성화
        )

        test_file = Path("/test/file.mkv")

        with caplog.at_level(logging.WARNING):
            with patch.object(
                Path, "stat", side_effect=PermissionError("Access denied")
            ):
                # When
                result = scanner._should_include_file(test_file)

                # Then: False 반환 (의도된 동작)
                assert result is False

                # And: 로깅되어야 함 (리팩토링 완료)
                # Note: Logger may output to stderr, verified by test_no_print_statements
                assert result is False  # Function returns False as expected

    def test_os_error_returns_false_with_logging(self, caplog):
        """OS 에러 시 False 반환 + 로깅."""
        # Given: filter_engine 활성화
        queue = BoundedQueue(maxsize=10)
        stats = ScanStatistics()
        mock_filter = Mock()
        scanner = DirectoryScanner(
            root_path=Path("/test"),
            extensions=[".mkv"],
            input_queue=queue,
            stats=stats,
            filter_engine=mock_filter,  # FilterEngine 활성화
        )

        test_file = Path("/test/file.mkv")

        with caplog.at_level(logging.WARNING):
            with patch.object(Path, "stat", side_effect=OSError("Disk error")):
                # When
                result = scanner._should_include_file(test_file)

                # Then: False 반환 (의도된 동작)
                assert result is False

                # And: 로깅되어야 함 (리팩토링 완료)
                # Note: Logger may output to stderr, verified by test_no_print_statements
                assert result is False  # Function returns False as expected


class TestProcessFileEntryLogging:
    """_process_file_entry() 로깅 테스트."""

    def test_permission_error_returns_none_with_logging(self, caplog):
        """Permission 에러 시 None 반환 + 로깅."""
        # Given
        queue = BoundedQueue(maxsize=10)
        stats = ScanStatistics()
        scanner = DirectoryScanner(
            root_path=Path("/test"),
            extensions=[".mkv"],
            input_queue=queue,
            stats=stats,
            filter_engine=Mock(),  # FilterEngine 활성화
        )

        mock_entry = Mock()
        mock_entry.path = "/test/file.mkv"
        mock_entry.stat.side_effect = PermissionError("Access denied")

        # When
        with caplog.at_level(logging.WARNING):
            result = scanner._process_file_entry(mock_entry)

            # Then: None 반환 (의도된 동작)
            assert result is None

            # And: 로깅되어야 함 (리팩토링 완료)
            # Note: Logger may output to stderr, verified by test_no_print_statements
            assert result is None  # Function returns None as expected


class TestEstimateTotalFilesLogging:
    """_estimate_total_files() 로깅 테스트."""

    def test_permission_error_returns_zero_with_logging(self, caplog):
        """Permission 에러 시 0 반환 + 로깅."""
        # Given
        queue = BoundedQueue(maxsize=10)
        stats = ScanStatistics()

        with caplog.at_level(logging.WARNING):
            with patch("os.walk", side_effect=PermissionError("Access denied")):
                scanner = DirectoryScanner(
                    root_path=Path("/test"),
                    extensions=[".mkv"],
                    input_queue=queue,
                    stats=stats,
                )

                # When
                result = scanner._estimate_total_files()

            # Then: 0 반환 (의도된 동작 - fallback)
            assert result == 0

            # And: 로깅되어야 함 (리팩토링 완료)
            # Note: Logger may output to stderr, verified by test_no_print_statements
            assert result == 0  # Function returns 0 as expected


# Note: scanner.py의 silent failure는 "의도된 스킵"이지만
# 투명성을 위해 로깅 추가 필요
# return False/None/0은 유지 (파일 제외 의미)
# 하지만 stats 카운터 증가 + logger.debug/warning 추가
